import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";
import * as k8s from "@pulumi/kubernetes";

// Basic config
const config = new pulumi.Config();
const project = gcp.config.project || config.require("gcp:project");
const region =
    gcp.config.region ||
    (gcp.config.zone ? gcp.config.zone.replace(/-[a-z]$/, "") : "us-central1");
const location = gcp.config.zone || region;
const nodeCount = config.getNumber("nodeCount") ?? 2;
const nodeMachineType = config.get("nodeMachineType") ?? "e2-standard-2";

// Images (set these via pulumi config set image:<name> ...)
const imageConfig = new pulumi.Config("image");
const coreEtlApiImage = imageConfig.require("coreEtlApi");
const ragServiceImage = imageConfig.require("ragService");
const calendarAgentImage = imageConfig.require("calendarAgent");
const ocrEngineImage = imageConfig.require("ocrEngine");
const frontendImage = imageConfig.require("frontend");

// App settings
const dbUser = config.get("dbUser") ?? "fitai";
const dbPassword = config.getSecret("dbPassword") ?? pulumi.secret("fitai");
const dbName = config.get("dbName") ?? "fitai_app";
const jwtSecret = config.getSecret("jwtSecret") ?? pulumi.secret("change-me-in-prod");
const ragQueryMethod = config.get("ragQueryMethod") ?? "char-split";
const ragQueryResults = config.getNumber("ragQueryResults") ?? 5;
const ragTimeoutSeconds = config.getNumber("ragTimeoutSeconds") ?? 30;
const frontendOrigin = config.get("frontendOrigin");
const openaiApiKey = config.requireSecret("openaiApiKey");
const corsAllowOrigins =
    config.get("corsAllowOrigins") ??
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://fitai-frontend:3000",
        "http://frontend:3000",
        "http://frontend-svc",
        "http://frontend-svc:80",
        "http://34.31.81.159",
        "http://34.31.81.159:3000",
        frontendOrigin,
    ]
        .filter(Boolean)
        .join(",");

// Optional GCP service account key for workloads that need local creds.
const gcpServiceAccountKey = config.getSecret("gcpServiceAccountKey");
const gcpCredsFileName =
    config.get("gcpCredsFileName") ?? "rich-access-471117-r0-f17d92fbf298.json";

// Network and subnetwork (since default network does not exist in project)
const network = new gcp.compute.Network("fitai-network", {
    autoCreateSubnetworks: false,
});

const subnetwork = new gcp.compute.Subnetwork("fitai-subnetwork", {
    ipCidrRange: "10.10.0.0/16",
    region: region,
    network: network.id,
    secondaryIpRanges: [
        { rangeName: "fitai-pods", ipCidrRange: "10.20.0.0/16" },
        { rangeName: "fitai-services", ipCidrRange: "10.30.0.0/20" },
    ],
});

// Allow external clients to reach our service ports (front-end LB on 80, APIs on 8001/8002/8004,
// and ocr on 8003). Custom VPCs do not have permissive ingress by default.
const ingressFirewall = new gcp.compute.Firewall("fitai-lb-ingress", {
    network: network.id,
    allows: [
        {
            protocol: "tcp",
            ports: ["80", "8001", "8002", "8003", "8004"],
        },
    ],
    sourceRanges: ["0.0.0.0/0"],
    direction: "INGRESS",
    description: "Allow external traffic to FitAI LBs and services",
});

// GKE cluster
const cluster = new gcp.container.Cluster("fitai-cluster", {
    location,
    network: network.id,
    subnetwork: subnetwork.id,
    ipAllocationPolicy: {
        clusterSecondaryRangeName: "fitai-pods",
        servicesSecondaryRangeName: "fitai-services",
    },
    removeDefaultNodePool: true,
    initialNodeCount: 1,
    releaseChannel: { channel: "REGULAR" },
    networkingMode: "VPC_NATIVE",
});

const nodePool = new gcp.container.NodePool("fitai-default-np", {
    cluster: cluster.name,
    location,
    initialNodeCount: nodeCount,
    nodeConfig: {
        machineType: nodeMachineType,
        // Keep disks small and on standard PD to stay under regional SSD quotas.
        diskType: "pd-standard",
        diskSizeGb: 50,
        oauthScopes: ["https://www.googleapis.com/auth/cloud-platform"],
        labels: { env: "pulumi" },
    },
});

// Kubeconfig wired to the new cluster
const kubeconfig = pulumi
    .all([cluster.name, cluster.endpoint, cluster.masterAuth, project])
    .apply(([name, endpoint, masterAuth, proj]) => {
        const context = `${proj}_${location}_${name}`;
        return `apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: ${masterAuth.clusterCaCertificate}
    server: https://${endpoint}
  name: ${context}
contexts:
- context:
    cluster: ${context}
    user: ${context}
  name: ${context}
current-context: ${context}
kind: Config
preferences: {}
users:
- name: ${context}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin (e.g., sudo apt-get install google-cloud-sdk-gke-gcloud-auth-plugin)
      provideClusterInfo: true
`;
    });

const provider = new k8s.Provider("gke", { kubeconfig });

// Namespace for all app resources
const ns = new k8s.core.v1.Namespace(
    "fitai-ns",
    { metadata: { name: "fitai" } },
    { provider }
);

const jwtSecretObj = new k8s.core.v1.Secret(
    "jwt-secret",
    {
        metadata: { namespace: ns.metadata.name, name: "jwt-secret" },
        stringData: { secret: jwtSecret },
    },
    { provider }
);

// Secret for Postgres password
const postgresSecret = new k8s.core.v1.Secret(
    "postgres-creds",
    {
        metadata: { namespace: ns.metadata.name, name: "postgres-creds" },
        stringData: { password: dbPassword },
    },
    { provider }
);

// Optional secret with GCP service account JSON
const gcpKeySecret = gcpServiceAccountKey
    ? new k8s.core.v1.Secret(
          "gcp-sa-key",
          {
              metadata: { namespace: ns.metadata.name, name: "gcp-sa-key" },
              stringData: { [gcpCredsFileName]: gcpServiceAccountKey },
          },
          { provider }
      )
    : undefined;

const gcpCredVolume = gcpKeySecret
    ? [
          {
              name: "gcp-creds",
              secret: { secretName: gcpKeySecret.metadata.name },
          },
      ]
    : [];
const gcpCredMount = gcpKeySecret
    ? [{ name: "gcp-creds", mountPath: "/secrets", readOnly: true }]
    : [];
const gcpCredsPath = gcpKeySecret ? `/secrets/${gcpCredsFileName}` : undefined;

// Postgres
const postgresPvc = new k8s.core.v1.PersistentVolumeClaim(
    "postgres-pvc",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            accessModes: ["ReadWriteOnce"],
            resources: { requests: { storage: "10Gi" } },
        },
    },
    { provider }
);

const postgresDeployment = new k8s.apps.v1.Deployment(
    "postgres",
    {
        metadata: { namespace: ns.metadata.name, name: "postgres" },
        spec: {
            strategy: { type: "Recreate" },
            replicas: 1,
            selector: { matchLabels: { app: "postgres" } },
            template: {
                metadata: { labels: { app: "postgres" } },
                spec: {
                    containers: [
                        {
                            name: "postgres",
                            image: "postgres:15",
                            ports: [{ containerPort: 5432 }],
                            env: [
                                { name: "POSTGRES_USER", value: dbUser },
                                {
                                    name: "POSTGRES_PASSWORD",
                                    valueFrom: {
                                        secretKeyRef: { name: postgresSecret.metadata.name, key: "password" },
                                    },
                                },
                                { name: "POSTGRES_DB", value: dbName },
                                { name: "PGDATA", value: "/var/lib/postgresql/data/pgdata" },
                            ],
                            volumeMounts: [
                                { name: "data", mountPath: "/var/lib/postgresql/data" },
                            ],
                        },
                    ],
                    volumes: [{ name: "data", persistentVolumeClaim: { claimName: postgresPvc.metadata.name } }],
                },
            },
        },
    },
    { provider, deleteBeforeReplace: true }
);

const postgresService = new k8s.core.v1.Service(
    "postgres-svc",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            selector: { app: "postgres" },
            ports: [{ port: 5432, targetPort: 5432 }],
        },
    },
    { provider }
);

// ChromaDB
const chromaPvc = new k8s.core.v1.PersistentVolumeClaim(
    "chromadb-pvc",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            accessModes: ["ReadWriteOnce"],
            resources: { requests: { storage: "10Gi" } },
        },
    },
    { provider }
);

const chromaDeployment = new k8s.apps.v1.Deployment(
    "chromadb",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            replicas: 1,
            selector: { matchLabels: { app: "chromadb" } },
            template: {
                metadata: { labels: { app: "chromadb" } },
                spec: {
                    containers: [
                        {
                            name: "chromadb",
                            image: "chromadb/chroma:latest",
                            ports: [{ containerPort: 8000 }],
                            env: [
                                { name: "IS_PERSISTENT", value: "TRUE" },
                                { name: "ANONYMIZED_TELEMETRY", value: "FALSE" },
                                { name: "CHROMA_CORS_ALLOW_ORIGINS", value: '["*"]' },
                            ],
                            volumeMounts: [
                                { name: "data", mountPath: "/data" },
                            ],
                        },
                    ],
                    volumes: [{ name: "data", persistentVolumeClaim: { claimName: chromaPvc.metadata.name } }],
                },
            },
        },
    },
    { provider }
);

const chromaService = new k8s.core.v1.Service(
    "chromadb-svc",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            selector: { app: "chromadb" },
            ports: [{ port: 8000, targetPort: 8000 }],
        },
    },
    { provider }
);

// Core ETL API
const coreEtlApi = new k8s.apps.v1.Deployment(
    "core-etl-api",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            replicas: 1,
            selector: { matchLabels: { app: "core-etl-api" } },
            template: {
                metadata: { labels: { app: "core-etl-api" } },
                spec: {
                    containers: [
                        {
                            name: "core-etl-api",
                            image: coreEtlApiImage,
                            ports: [{ containerPort: 8001 }],
                            env: [
                                { name: "POSTGRES_USER", value: dbUser },
                                { name: "POSTGRES_PASSWORD", valueFrom: { secretKeyRef: { name: "postgres-creds", key: "password" } } },
                                { name: "POSTGRES_DB", value: dbName },
                                { name: "POSTGRES_HOST", value: postgresService.metadata.name },
                                { name: "POSTGRES_PORT", value: "5432" },
                                {
                                    name: "JWT_SECRET",
                                    valueFrom: {
                                        secretKeyRef: { name: jwtSecretObj.metadata.name, key: "secret" },
                                    },
                                },
                                { name: "JWT_EXPIRE_MINUTES", value: "120" },
                                ...(gcpCredsPath ? [{ name: "GOOGLE_APPLICATION_CREDENTIALS", value: gcpCredsPath }] : []),
                            ],
                            volumeMounts: gcpCredMount,
                        },
                    ],
                    volumes: gcpCredVolume,
                },
            },
        },
    },
    { provider }
);

const coreEtlService = new k8s.core.v1.Service(
    "core-etl-svc",
    {
        metadata: { namespace: ns.metadata.name, name: "core-etl-svc" },
        spec: {
            type: "LoadBalancer",
            selector: { app: "core-etl-api" },
            ports: [{ port: 8001, targetPort: 8001 }],
        },
    },
    { provider }
);

// RAG Service
const ragService = new k8s.apps.v1.Deployment(
    "rag-service",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            replicas: 1,
            selector: { matchLabels: { app: "rag-service" } },
            template: {
                metadata: { labels: { app: "rag-service" } },
                spec: {
                    containers: [
                        {
                            name: "rag-service",
                            image: ragServiceImage,
                            ports: [{ containerPort: 8002 }],
                            env: [
                                ...(gcpCredsPath ? [{ name: "GOOGLE_APPLICATION_CREDENTIALS", value: gcpCredsPath }] : []),
                                { name: "GCP_PROJECT", value: project },
                                { name: "CHROMADB_HOST", value: chromaService.metadata.name },
                                { name: "CHROMADB_PORT", value: "8000" },
                                { name: "CORS_ALLOW_ORIGINS", value: corsAllowOrigins },
                            ],
                            volumeMounts: gcpCredMount,
                        },
                    ],
                    volumes: gcpCredVolume,
                },
            },
        },
    },
    { provider }
);

const ragServiceSvc = new k8s.core.v1.Service(
    "rag-service-svc",
    {
        metadata: { namespace: ns.metadata.name, name: "rag-service-svc" },
        spec: {
            type: "LoadBalancer",
            selector: { app: "rag-service" },
            ports: [{ port: 8002, targetPort: 8002 }],
        },
    },
    { provider }
);

// Calendar Agent
const calendarAgent = new k8s.apps.v1.Deployment(
    "calendar-agent",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            replicas: 1,
            selector: { matchLabels: { app: "calendar-agent" } },
            template: {
                metadata: { labels: { app: "calendar-agent" } },
                spec: {
                    containers: [
                        {
                            name: "calendar-agent",
                            image: calendarAgentImage,
                            ports: [{ containerPort: 8004 }],
                            env: [
                                { name: "POSTGRES_USER", value: dbUser },
                                { name: "POSTGRES_PASSWORD", valueFrom: { secretKeyRef: { name: "postgres-creds", key: "password" } } },
                                { name: "POSTGRES_DB", value: dbName },
                                { name: "POSTGRES_HOST", value: postgresService.metadata.name },
                                { name: "POSTGRES_PORT", value: "5432" },
                                {
                                    name: "RAG_SERVICE_URL",
                                    value: pulumi.interpolate`http://${ragServiceSvc.metadata.name}:8002`,
                                },
                                { name: "RAG_QUERY_METHOD", value: ragQueryMethod },
                                { name: "RAG_QUERY_RESULTS", value: ragQueryResults.toString() },
                                { name: "RAG_TIMEOUT_SECONDS", value: ragTimeoutSeconds.toString() },
                                { name: "CORS_ALLOW_ORIGINS", value: corsAllowOrigins },
                                ...(gcpCredsPath
                                    ? [{ name: "GOOGLE_APPLICATION_CREDENTIALS", value: gcpCredsPath }]
                                    : []),
                                ...(openaiApiKey ? [{ name: "OPENAI_API_KEY", value: openaiApiKey }] : []),
                            ],
                            volumeMounts: gcpCredMount,
                        },
                    ],
                    volumes: gcpCredVolume,
                },
            },
        },
    },
    { provider }
);

const calendarService = new k8s.core.v1.Service(
    "calendar-agent-svc",
    {
        metadata: { namespace: ns.metadata.name, name: "calendar-agent-svc" },
        spec: {
            type: "LoadBalancer",
            selector: { app: "calendar-agent" },
            ports: [{ port: 8004, targetPort: 8004 }],
        },
    },
    { provider }
);

// OCR Engine
const ocrEngine = new k8s.apps.v1.Deployment(
    "ocr-engine",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            replicas: 1,
            selector: { matchLabels: { app: "ocr-engine" } },
            template: {
                metadata: { labels: { app: "ocr-engine" } },
                spec: {
                    containers: [
                        {
                            name: "ocr-engine",
                            image: ocrEngineImage,
                            ports: [{ containerPort: 8003 }],
                            env: [
                                ...(gcpCredsPath ? [{ name: "GOOGLE_APPLICATION_CREDENTIALS", value: gcpCredsPath }] : []),
                            ],
                            volumeMounts: gcpCredMount,
                        },
                    ],
                    volumes: gcpCredVolume,
                },
            },
        },
    },
    { provider }
);

const ocrService = new k8s.core.v1.Service(
    "ocr-engine-svc",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            selector: { app: "ocr-engine" },
            ports: [{ port: 8003, targetPort: 8003 }],
        },
    },
    { provider }
);

// Frontend (exposed)
const frontend = new k8s.apps.v1.Deployment(
    "frontend",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            replicas: 1,
            selector: { matchLabels: { app: "frontend" } },
            template: {
                metadata: { labels: { app: "frontend" } },
                spec: {
                    containers: [
                        {
                            name: "frontend",
                            image: frontendImage,
                            ports: [{ containerPort: 3000 }],
                            env: [
                                {
                                    name: "NEXT_PUBLIC_PIPELINE_URL",
                                    value: pulumi.interpolate`http://${coreEtlService.status.loadBalancer.ingress[0].ip}:8001`,
                                },
                                {
                                    name: "NEXT_PUBLIC_CALENDAR_AGENT_URL",
                                    value: pulumi.interpolate`http://${calendarService.status.loadBalancer.ingress[0].ip}:8004`,
                                },
                                {
                                    name: "NEXT_PUBLIC_RAG_URL",
                                    value: pulumi.interpolate`http://${ragServiceSvc.status.loadBalancer.ingress[0].ip}:8002`,
                                },
                            ],
                        },
                    ],
                },
            },
        },
    },
    { provider }
);

const frontendService = new k8s.core.v1.Service(
    "frontend-svc",
    {
        metadata: { namespace: ns.metadata.name },
        spec: {
            type: "LoadBalancer",
            selector: { app: "frontend" },
            ports: [{ port: 80, targetPort: 3000 }],
        },
    },
    { provider }
);

// Exports
export const kubeconfigOut = kubeconfig;
export const frontendIp = frontendService.status.loadBalancer.ingress[0].ip;
export const coreEtlIp = coreEtlService.status.loadBalancer.ingress[0].ip;
export const ragServiceIp = ragServiceSvc.status.loadBalancer.ingress[0].ip;
export const calendarAgentIp = calendarService.status.loadBalancer.ingress[0].ip;
