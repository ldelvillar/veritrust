export type HelpCategoryIconName =
  | 'star'
  | 'report'
  | 'shield'
  | 'settings'
  | 'lock'
  | 'warning';

export interface HelpCategory {
  slug: string;
  tint: string;
  color: string;
  title: string;
  desc: string;
  icon: HelpCategoryIconName;
}

export interface HelpStep {
  n: string;
  title: string;
  desc: string;
  tags: string[];
}

export interface HelpFaqItem {
  cat: string;
  q: string;
  a: string;
}

export interface HelpArticle {
  id: string;
  category: string;
  title: string;
  summary: string;
  tags: string[];
}

export const CATEGORIES = [
  {
    slug: 'primeros-pasos',
    tint: '#eeebfc',
    color: '#5446dc',
    title: 'Primeros pasos',
    desc: 'Lanza tu primer análisis en menos de un minuto.',
    icon: 'star',
  },
  {
    slug: 'leer-informe',
    tint: '#e4f1fc',
    color: '#2c97e8',
    title: 'Cómo leer un informe',
    desc: 'Puntuación, afirmaciones, veredictos y confianza.',
    icon: 'report',
  },
  {
    slug: 'fuentes-metodologia',
    tint: '#def4ea',
    color: '#13b877',
    title: 'Fuentes y metodología',
    desc: 'OMS, Cochrane y NIH: cómo verificamos cada dato.',
    icon: 'shield',
  },
  {
    slug: 'cuenta-planes',
    tint: '#fbefda',
    color: '#d98e29',
    title: 'Cuenta y planes',
    desc: 'Consumo, facturación y gestión del equipo.',
    icon: 'settings',
  },
  {
    slug: 'privacidad-datos',
    tint: '#eeebfc',
    color: '#5446dc',
    title: 'Privacidad y datos',
    desc: 'Cómo tratamos y protegemos tu contenido.',
    icon: 'lock',
  },
  {
    slug: 'solucion-problemas',
    tint: '#fbe4e8',
    color: '#e0556b',
    title: 'Solución de problemas',
    desc: 'Errores frecuentes y cómo resolverlos.',
    icon: 'warning',
  },
] satisfies HelpCategory[];

export const STEPS = [
  {
    n: '1',
    title: 'Aporta el contenido',
    desc: 'Pega un texto, introduce un enlace o sube un documento. El extractor leerá texto, tablas y pies de imagen.',
    tags: ['Texto', 'Enlace', 'Archivo'],
  },
  {
    n: '2',
    title: 'Tres agentes verifican',
    desc: 'El Extractor aísla las afirmaciones, el Traductor normaliza la terminología clínica y el Experto las contrasta con fuentes.',
    tags: ['Extractor', 'Traductor', 'Experto'],
  },
  {
    n: '3',
    title: 'Lee tu informe',
    desc: 'Recibe una puntuación de credibilidad explicada, afirmación por afirmación y con sus fuentes citadas.',
    tags: ['Puntuación', 'Afirmaciones', 'Fuentes'],
  },
] satisfies HelpStep[];

export const FAQ = [
  {
    cat: 'Uso',
    q: '¿Veritrust sustituye el consejo médico?',
    a: 'No. Veritrust es una herramienta de verificación orientativa que evalúa la credibilidad de la información. <b>No sustituye</b> el diagnóstico ni el consejo de un profesional sanitario.',
  },
  {
    cat: 'Privacidad',
    q: '¿Se guarda el contenido que analizo?',
    a: 'El contenido se procesa de forma privada y <b>no se usa para entrenar modelos</b>. Puedes eliminar cualquier análisis desde «Análisis anteriores».',
  },
  {
    cat: 'Informe',
    q: '¿Cómo se calcula la puntuación de credibilidad?',
    a: 'Cada afirmación se contrasta con fuentes médicas (OMS, Cochrane, NIH) y se pondera por su nivel de evidencia. La media ponderada da la puntuación de 0 a 100.',
  },
  {
    cat: 'Uso',
    q: '¿Cuánto tarda un análisis?',
    a: 'La mayoría de análisis se completan en 30–60 segundos. Textos muy largos o documentos con muchas afirmaciones pueden tardar algo más.',
  },
  {
    cat: 'Uso',
    q: '¿Puedo analizar imágenes o capturas?',
    a: 'Sí. El Extractor lee texto, tablas y pies de imagen en archivos PDF, DOCX, TXT, PNG y JPG (hasta 10 MB).',
  },
  {
    cat: 'Informe',
    q: '¿Qué significa el nivel de confianza?',
    a: 'Indica cuánta evidencia concordante respalda el veredicto. Una confianza baja sugiere revisar las fuentes antes de tomar una decisión.',
  },
] satisfies HelpFaqItem[];

export const POPULAR = [
  'Mi primer análisis',
  'Leer la puntuación',
  'Fuentes médicas',
];

export const ARTICLES = [
  {
    id: 'mi-primer-analisis',
    category: 'Primeros pasos',
    title: 'Mi primer análisis',
    summary:
      'Pega una afirmación médica, añade un enlace o carga un documento, revisa que el contenido sea legible y lanza el análisis desde la vista principal.',
    tags: ['Inicio', 'Texto', 'Enlace'],
  },
  {
    id: 'elegir-texto-enlace-archivo',
    category: 'Primeros pasos',
    title: 'Elegir entre texto, enlace o archivo',
    summary:
      'Usa texto pegado para mensajes cortos, enlaces para artículos públicos y archivos cuando necesites analizar documentos completos o capturas.',
    tags: ['Texto', 'URL', 'Archivo'],
  },
  {
    id: 'preparar-documentos-largos',
    category: 'Primeros pasos',
    title: 'Preparar documentos largos',
    summary:
      'Divide informes extensos por secciones, conserva los encabezados clínicos y evita mezclar varios temas médicos en una sola solicitud.',
    tags: ['PDF', 'DOCX', 'Formato'],
  },
  {
    id: 'analisis-pendiente',
    category: 'Primeros pasos',
    title: 'Qué ocurre mientras el análisis está pendiente',
    summary:
      'El análisis queda en cola mientras los agentes extraen afirmaciones, normalizan el lenguaje y contrastan la evidencia antes de guardar el resultado.',
    tags: ['Pendiente', 'Cola', 'Proceso'],
  },
  {
    id: 'estado-de-un-analisis',
    category: 'Primeros pasos',
    title: 'Interpretar el estado de un análisis',
    summary:
      'Pendiente indica que el trabajo sigue activo, completado muestra el informe final y fallido señala que conviene revisar el contenido o reintentarlo.',
    tags: ['Estado', 'Informe', 'Error'],
  },
  {
    id: 'guardar-resultados-anteriores',
    category: 'Primeros pasos',
    title: 'Guardar y revisar resultados anteriores',
    summary:
      'Consulta el historial para recuperar análisis previos, filtrar por origen, ordenar por puntuación y eliminar entradas que ya no necesitas.',
    tags: ['Historial', 'Filtros', 'Eliminar'],
  },
  {
    id: 'leer-la-puntuacion',
    category: 'Cómo leer un informe',
    title: 'Leer la puntuación',
    summary:
      'La puntuación resume la credibilidad del contenido en una escala de 0 a 100 y debe leerse junto con las afirmaciones y la confianza.',
    tags: ['Puntuación', 'Credibilidad', 'Informe'],
  },
  {
    id: 'veredicto-verdadera-falsa',
    category: 'Cómo leer un informe',
    title: 'Entender el veredicto verdadera o falsa',
    summary:
      'El veredicto marca la dirección principal de la evidencia disponible; revisa la explicación cuando haya matices, excepciones o contexto clínico.',
    tags: ['Veredicto', 'Evidencia', 'Contexto'],
  },
  {
    id: 'nivel-de-confianza',
    category: 'Cómo leer un informe',
    title: 'Nivel de confianza',
    summary:
      'La confianza refleja la solidez y coherencia de las fuentes encontradas, no la gravedad médica ni la importancia personal de la decisión.',
    tags: ['Confianza', 'Fuentes', 'Riesgo'],
  },
  {
    id: 'afirmaciones-detectadas',
    category: 'Cómo leer un informe',
    title: 'Afirmaciones detectadas',
    summary:
      'Cada afirmación se revisa por separado para distinguir datos verificables, opiniones, recomendaciones generales y frases sin contenido médico comprobable.',
    tags: ['Afirmaciones', 'Extractor', 'Detalle'],
  },
  {
    id: 'explicacion-recomendaciones',
    category: 'Cómo leer un informe',
    title: 'Explicación y recomendaciones',
    summary:
      'La explicación resume por qué se asignó el veredicto y señala cuándo conviene consultar fuentes adicionales o a un profesional sanitario.',
    tags: ['Explicación', 'Revisión', 'Salud'],
  },
  {
    id: 'fuentes-medicas',
    category: 'Fuentes y metodología',
    title: 'Fuentes médicas',
    summary:
      'VeriTrust prioriza organismos sanitarios, revisiones sistemáticas, guías clínicas y literatura biomédica reconocida para contrastar afirmaciones.',
    tags: ['OMS', 'Cochrane', 'NIH'],
  },
  {
    id: 'seleccion-de-evidencia',
    category: 'Fuentes y metodología',
    title: 'Cómo seleccionamos evidencia',
    summary:
      'Las fuentes se valoran por autoridad, actualidad, consenso, aplicabilidad clínica y concordancia con la afirmación concreta analizada.',
    tags: ['Metodología', 'Consenso', 'Calidad'],
  },
  {
    id: 'actualizacion-referencias',
    category: 'Fuentes y metodología',
    title: 'Actualización de referencias',
    summary:
      'Los resultados pueden cambiar cuando aparecen nuevas guías o estudios; repite el análisis si el contenido depende de evidencia muy reciente.',
    tags: ['Actualización', 'Guías', 'Estudios'],
  },
  {
    id: 'limites-metodologicos',
    category: 'Fuentes y metodología',
    title: 'Límites metodológicos',
    summary:
      'La herramienta no diagnostica, no sustituye atención médica y puede mostrar baja confianza cuando la afirmación es ambigua o carece de contexto.',
    tags: ['Límites', 'Diagnóstico', 'Contexto'],
  },
  {
    id: 'crear-configurar-cuenta',
    category: 'Cuenta y planes',
    title: 'Crear y configurar cuenta',
    summary:
      'Completa el acceso, verifica tu correo y revisa el perfil para que el equipo pueda asociar análisis, historial y permisos correctamente.',
    tags: ['Cuenta', 'Perfil', 'Acceso'],
  },
  {
    id: 'invitar-miembros-equipo',
    category: 'Cuenta y planes',
    title: 'Invitar miembros del equipo',
    summary:
      'Añade usuarios con el correo corporativo, asigna permisos según su función y revisa periódicamente quién conserva acceso al espacio.',
    tags: ['Equipo', 'Invitaciones', 'Permisos'],
  },
  {
    id: 'cuotas-y-consumo',
    category: 'Cuenta y planes',
    title: 'Cuotas y consumo',
    summary:
      'El consumo depende del número de análisis, el tamaño del contenido y la complejidad de las afirmaciones detectadas en cada solicitud.',
    tags: ['Cuotas', 'Consumo', 'Límites'],
  },
  {
    id: 'cambiar-plan',
    category: 'Cuenta y planes',
    title: 'Cambiar de plan',
    summary:
      'Revisa el uso actual antes de ampliar o reducir el plan; los cambios deben alinearse con el volumen de análisis previsto por el equipo.',
    tags: ['Plan', 'Uso', 'Equipo'],
  },
  {
    id: 'facturacion-recibos',
    category: 'Cuenta y planes',
    title: 'Facturación y recibos',
    summary:
      'Mantén actualizados los datos fiscales y revisa los recibos para confirmar fechas, concepto, plan contratado y método de pago.',
    tags: ['Facturación', 'Recibos', 'Pago'],
  },
  {
    id: 'permisos-roles',
    category: 'Cuenta y planes',
    title: 'Permisos y roles',
    summary:
      'Los permisos ayudan a separar quienes pueden analizar contenido, consultar historial, gestionar usuarios o modificar ajustes del espacio.',
    tags: ['Roles', 'Seguridad', 'Equipo'],
  },
  {
    id: 'cerrar-cuenta',
    category: 'Cuenta y planes',
    title: 'Cerrar cuenta',
    summary:
      'Antes de cerrar una cuenta, exporta la información que necesites, elimina análisis sensibles y confirma que no quedan usuarios activos.',
    tags: ['Cuenta', 'Cierre', 'Datos'],
  },
  {
    id: 'contenido-retencion',
    category: 'Privacidad y datos',
    title: 'Contenido analizado y retención',
    summary:
      'El contenido enviado se utiliza para producir el informe solicitado y se conserva únicamente para mostrar historial y trazabilidad al usuario.',
    tags: ['Retención', 'Historial', 'Privacidad'],
  },
  {
    id: 'eliminar-analisis',
    category: 'Privacidad y datos',
    title: 'Eliminar análisis',
    summary:
      'Desde el historial puedes borrar análisis que ya no necesites; confirma la acción solo cuando no vayas a reutilizar ese resultado.',
    tags: ['Eliminar', 'Historial', 'Datos'],
  },
  {
    id: 'datos-sensibles',
    category: 'Privacidad y datos',
    title: 'Protección de datos sensibles',
    summary:
      'Evita incluir identificadores personales innecesarios y anonimiza casos clínicos antes de analizarlos cuando trabajes con datos sensibles.',
    tags: ['Anonimización', 'Datos', 'Seguridad'],
  },
  {
    id: 'analisis-lento',
    category: 'Solución de problemas',
    title: 'El análisis tarda más de lo esperado',
    summary:
      'Los textos extensos, documentos con muchas afirmaciones o picos de cola pueden retrasar el resultado; espera unos minutos antes de reintentar.',
    tags: ['Pendiente', 'Tiempo', 'Cola'],
  },
  {
    id: 'enlace-no-legible',
    category: 'Solución de problemas',
    title: 'No se puede leer un enlace',
    summary:
      'Algunos sitios bloquean la extracción o requieren sesión; copia el texto relevante o sube un documento si el enlace no se procesa.',
    tags: ['URL', 'Extracción', 'Acceso'],
  },
  {
    id: 'archivo-no-soportado',
    category: 'Solución de problemas',
    title: 'Archivo no soportado',
    summary:
      'Comprueba que el archivo sea PDF, DOCX, TXT, PNG o JPG y que no supere el tamaño máximo permitido antes de volver a cargarlo.',
    tags: ['Archivo', 'Formato', 'Carga'],
  },
  {
    id: 'baja-confianza',
    category: 'Solución de problemas',
    title: 'Resultados con baja confianza',
    summary:
      'Una confianza baja suele aparecer con afirmaciones vagas, evidencia insuficiente o temas muy recientes; añade contexto y repite el análisis.',
    tags: ['Confianza', 'Evidencia', 'Contexto'],
  },
  {
    id: 'falsos-positivos',
    category: 'Solución de problemas',
    title: 'Falsos positivos',
    summary:
      'Si una afirmación correcta aparece marcada como falsa, revisa si faltaba contexto, había ironía o el texto mezclaba varias afirmaciones distintas.',
    tags: ['Veredicto', 'Contexto', 'Revisión'],
  },
  {
    id: 'errores-autenticacion',
    category: 'Solución de problemas',
    title: 'Errores de autenticación',
    summary:
      'Cierra sesión, vuelve a entrar y confirma que tu cuenta sigue activa si el panel muestra errores al cargar datos protegidos.',
    tags: ['Acceso', 'Sesión', 'Cuenta'],
  },
  {
    id: 'limite-tamano',
    category: 'Solución de problemas',
    title: 'Límite de tamaño',
    summary:
      'Reduce el contenido a las secciones relevantes o divide el documento si aparece un error relacionado con tamaño, longitud o carga.',
    tags: ['Límite', 'Documento', 'Carga'],
  },
  {
    id: 'contactar-soporte-contexto',
    category: 'Solución de problemas',
    title: 'Contactar soporte con contexto',
    summary:
      'Incluye el tipo de contenido, la hora aproximada, el estado mostrado y el mensaje de error para que soporte pueda investigar con rapidez.',
    tags: ['Soporte', 'Error', 'Contexto'],
  },
] satisfies HelpArticle[];
