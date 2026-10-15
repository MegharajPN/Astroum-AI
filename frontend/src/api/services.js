// One function per backend endpoint. Pages import from here, never call fetch directly.
import { apiGet, apiPatch, apiPost } from './client.js'

export const getDashboard = () => apiGet('/dashboard/')
export const searchProducts = (params) => apiGet('/products/', params)
export const getProduct = (id) => apiGet(`/products/${id}/`)
export const searchNlem = (params) => apiGet('/nlem/', params)
export const searchJanAushadhi = (params) => apiGet('/jan-aushadhi/', params)
export const searchRegulatoryEvents = (params) => apiGet('/regulatory-events/', params)
export const checkInteractions = (ingredients) => apiGet('/interactions/check/', { ingredients })
export const listInteractionSeeds = (params) => apiGet('/interactions/', params)
export const getStock = (params) => apiGet('/stock/', params)
export const getStockSummary = () => apiGet('/stock-summary/')
export const searchProtocolUnits = (params) => apiGet('/protocol-units/', params)
export const listProtocols = (params) => apiGet('/protocols/', params)
export const listGaps = (params) => apiGet('/gaps/', params)
export const createGap = (body) => apiPost('/gaps/', body)
export const resolveGap = (id, body) => apiPatch(`/gaps/${id}/`, body)
