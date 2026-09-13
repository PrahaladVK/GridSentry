import axios from "axios";

const client = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 20000,
});

export const getBuildings = () => client.get("/buildings").then((r) => r.data);

export const getForecast = (floor, horizon) =>
  client.get("/forecast", { params: { floor, horizon } }).then((r) => r.data);

export const getForecastHistory = (floor, horizon, limit = 60) =>
  client.get("/forecast/history", { params: { floor, horizon, limit } }).then((r) => r.data);

export const getLiveSeries = (floor, hours = 72) =>
  client.get("/forecast/live", { params: { floor, hours } }).then((r) => r.data);

export const getModelRuns = () => client.get("/forecast/models").then((r) => r.data);

export const getAnomalies = (params = {}) =>
  client.get("/anomalies", { params }).then((r) => r.data);

export const updateAnomalyStatus = (id, status) =>
  client.patch(`/anomalies/${id}`, { status }).then((r) => r.data);

export const getRecommendations = () => client.get("/recommendations").then((r) => r.data);

export const triggerRetrain = () => client.post("/retrain").then((r) => r.data);

export default client;
