import { http } from './client.js';

const RESOURCE = '/complaints';

export const complaintApi = {
  list: (params) => http.get(RESOURCE, params),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id) => http.delete(`${RESOURCE}/${id}`),
  classify: (content) => http.post(`${RESOURCE}/classify`, { content }),
  assign: (id, payload) => http.post(`${RESOURCE}/${id}/assign`, payload),
  finish: (id, payload) => http.post(`${RESOURCE}/${id}/finish`, payload),
  addFollowUp: (id, payload) => http.post(`${RESOURCE}/${id}/follow-ups`, payload),
  close: (id, payload) => http.post(`${RESOURCE}/${id}/close`, payload),
};
