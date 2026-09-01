export const PAGE_SIZE = 10;

// Consulta que precarga el servidor; el cliente solo reusa initialData si su ruta coincide.
export const INITIAL_HISTORY_PATH = `/history?page=1&page_size=${PAGE_SIZE}&source_type=all&verdict=all&status=all&date_range=all&sort=recent`;
