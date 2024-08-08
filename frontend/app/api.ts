import { ConnectPayload, HealthPayload, ConfigResponse } from "./api_types";

const checkUrl = async (url: string): Promise<boolean> => {
  try {
    const response = await fetch(url);
    return response.ok;
  } catch (error) {
    console.error(`Failed to fetch from ${url}:`, error);
    return false;
  }
};

export const detectHost = async (): Promise<string> => {
  const localUrl = "http://localhost:8000/api/health";
  const rootUrl = "/api/health";

  const isLocalHealthy = await checkUrl(localUrl);
  if (isLocalHealthy) {
    return "http://localhost:8000";
  }

  const isRootHealthy = await checkUrl(rootUrl);
  if (isRootHealthy) {
    const root = window.location.origin;
    return root;
  }

  throw new Error("Both health checks failed, please check the Verba Server");
};

export const fetchData = async <T>(endpoint: string): Promise<T | null> => {
  try {
    const host = await detectHost();
    const response = await fetch(`${host}${endpoint}`, { method: "GET" });
    const data = await response.json();

    if (!data) {
      console.warn(`Could not retrieve data from ${endpoint}`);
    }

    return data;
  } catch (error) {
    console.error(`Failed to fetch data from ${endpoint}:`, error);
    return null;
  }
};

export const fetchHealth = (): Promise<HealthPayload | null> =>
  fetchData<HealthPayload>("/api/health");

export const fetchConfig = (): Promise<ConfigResponse | null> =>
  fetchData<ConfigResponse>("/api/config");

export const connectToVerba = async (
  deployment: string,
  url: string,
  apiKey: string
): Promise<ConnectPayload | null> => {
  const host = await detectHost();
  const response = await fetch(`${host}/api/connect`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      deployment: deployment,
      weaviateURL: url,
      weaviateAPIKey: apiKey,
    }),
  });
  const data = await response.json();
  return data;
};
