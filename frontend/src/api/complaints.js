import { http } from './client.js';

const RESOURCE = '/complaints';

export const complaintApi = {
  list: (params) => http.get(RESOURCE, params),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id) => http.delete(`${RESOURCE}/${id}`),
  classify: (content) => http.post(`${RESOURCE}/classify`, { content }),
  transitions: (id) => http.get(`${RESOURCE}/${id}/transitions`),
  changeStatus: (id, payload) => http.post(`${RESOURCE}/${id}/transitions`, payload),
  addVisit: (id, payload) => http.post(`${RESOURCE}/${id}/visits`, payload),
};
