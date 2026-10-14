export type HelpCategoryIconName =
  'star' | 'report' | 'shield' | 'settings' | 'lock' | 'warning';

export interface HelpCategory {
  slug: string;
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
    title: 'Primeros pasos',
    desc: 'Lanza tu primer análisis en menos de un minuto.',
    icon: 'star',
  },
  {
    slug: 'leer-informe',
    title: 'Cómo leer un informe',
    desc: 'Puntuación, afirmaciones, veredictos y confianza.',
    icon: 'report',
  },
  {
    slug: 'fuentes-metodologia',
    title: 'Fuentes y metodología',
    desc: 'PubMed, Europe PMC, openFDA y CIMA: cómo verificamos cada dato.',
    icon: 'shield',
  },
  {
    slug: 'cuenta-planes',
    title: 'Cuenta y planes',
    desc: 'Tu cuenta, límites de uso y planes.',
    icon: 'settings',
  },
  {
    slug: 'privacidad-datos',
    title: 'Privacidad y datos',
    desc: 'Cómo tratamos y protegemos tu contenido.',
    icon: 'lock',
  },
  {
    slug: 'solucion-problemas',
    title: 'Solución de problemas',
    desc: 'Errores frecuentes y cómo resolverlos.',
    icon: 'warning',
  },
] satisfies HelpCategory[];

export const STEPS = [
  {
    n: '1',
    title: 'Aporta el contenido',
    desc: 'Pega un texto, introduce un enlace o sube un documento (PDF, TXT o MD). El extractor leerá su contenido.',
    tags: ['Texto', 'Enlace', 'Archivo'],
  },
  {
    n: '2',
    title: 'Los agentes verifican',
    desc: 'El Extractor aísla las afirmaciones, el Traductor normaliza la terminología clínica, el Investigador busca evidencia biomédica y valora cada fuente, y el Experto explica el veredicto.',
    tags: ['Extractor', 'Traductor', 'Investigador', 'Experto'],
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
    a: 'Sí: se guarda en tu historial hasta que lo eliminas, y <b>no se usa para entrenar modelos</b>. Puedes eliminar cualquier análisis, o todo el historial, desde «Análisis anteriores».',
  },
  {
    cat: 'Informe',
    q: '¿Cómo se calcula la puntuación de credibilidad?',
    a: 'Cada afirmación se contrasta con la literatura biomédica: las fuentes que la respaldan o la contradicen deciden su veredicto. La puntuación de 0 a 100 sale del veredicto del análisis y de su confianza (cerca de 100, verdadero; cerca de 0, falso) y se modera cuando la evidencia es escasa. Los análisis dudosos o parcialmente falsos no tienen puntuación.',
  },
  {
    cat: 'Uso',
    q: '¿Cuánto tarda un análisis?',
    a: 'Un análisis suele tardar menos de un minuto. Los textos largos con muchas afirmaciones, o los que esperan en cola detrás de otros análisis, pueden tardar unos minutos.',
  },
  {
    cat: 'Uso',
    q: '¿Puedo analizar imágenes o capturas?',
    a: 'Todavía no admitimos imágenes ni capturas como archivo. Los formatos válidos son <b>PDF, TXT y MD</b> (hasta 10 MB); si tienes una captura, copia el texto y pégalo directamente.',
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
      'Usa texto pegado para mensajes cortos, enlaces para artículos públicos y archivos cuando necesites analizar documentos completos.',
    tags: ['Texto', 'URL', 'Archivo'],
  },
  {
    id: 'preparar-documentos-largos',
    category: 'Primeros pasos',
    title: 'Preparar documentos largos',
    summary:
      'Se analizan los primeros 10.000 caracteres y se buscan fuentes para hasta 8 afirmaciones por análisis: divide los informes extensos por secciones y evita mezclar varios temas médicos en una sola solicitud.',
    tags: ['PDF', 'TXT', 'Formato'],
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
      'El veredicto marca la dirección principal de la evidencia disponible; si el texto mezcla afirmaciones falsas con otras respaldadas, es «parcialmente falso». Revisa el desglose por afirmación y la explicación cuando haya matices.',
    tags: ['Veredicto', 'Evidencia', 'Contexto'],
  },
  {
    id: 'nivel-de-confianza',
    category: 'Cómo leer un informe',
    title: 'Nivel de confianza',
    summary:
      'La confianza refleja cuántas fuentes coinciden en el mismo sentido y cuántas afirmaciones tienen evidencia; no mide la calidad de cada estudio ni la gravedad médica.',
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
      'Cada afirmación se busca en PubMed, Europe PMC y openFDA, y en CIMA (AEMPS) cuando nombra un medicamento. El informe enlaza cada fuente para que puedas leerla.',
    tags: ['PubMed', 'Europe PMC', 'openFDA', 'CIMA'],
  },
  {
    id: 'seleccion-de-evidencia',
    category: 'Fuentes y metodología',
    title: 'Cómo seleccionamos evidencia',
    summary:
      'Por cada afirmación se recuperan hasta 3 resultados de cada fuente; un modelo de IA valora si cada uno la respalda, la contradice o no es concluyente, y descarta los que no tratan de ella. Una regla fija decide el veredicto con esas valoraciones, sin ponderar la calidad de cada estudio; si la evidencia no basta, el veredicto es «Dudoso».',
    tags: ['Metodología', 'Evidencia', 'Veredicto'],
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
      'La herramienta no diagnostica ni sustituye la atención médica. Puede equivocarse, sobre todo con afirmaciones formuladas en negativo, y responde «Dudoso» cuando la literatura científica no trata el tema, como ocurre con muchos mitos populares.',
    tags: ['Límites', 'Diagnóstico', 'Contexto'],
  },
  {
    id: 'crear-configurar-cuenta',
    category: 'Cuenta y planes',
    title: 'Crear y configurar cuenta',
    summary:
      'Regístrate y verifica tu correo. Tus análisis y tu historial quedan asociados a tu cuenta y solo tú puedes verlos, salvo los que compartas con un enlace público.',
    tags: ['Cuenta', 'Perfil', 'Acceso'],
  },
  {
    id: 'uso-en-equipo',
    category: 'Cuenta y planes',
    title: 'Usar VeriTrust en equipo',
    summary:
      'Las cuentas de equipo aún no están disponibles: cada persona usa su propia cuenta y su propio historial. Si quieres probar VeriTrust con tu redacción, pulsa «Agendar demo».',
    tags: ['Equipo', 'Cuenta', 'Demo'],
  },
  {
    id: 'limites-de-uso',
    category: 'Cuenta y planes',
    title: 'Límites de uso',
    summary:
      'Puedes lanzar hasta 5 análisis por minuto; si superas el límite, espera un momento y vuelve a intentarlo. Los textos pegados admiten hasta 10.000 caracteres y los archivos, hasta 10 MB.',
    tags: ['Límites', 'Uso', 'Tamaño'],
  },
  {
    id: 'planes-de-pago',
    category: 'Cuenta y planes',
    title: 'Planes de pago',
    summary:
      'Los planes Pro y Equipo están en acceso anticipado: apúntate desde la página de precios y te avisaremos cuando abran.',
    tags: ['Plan', 'Pro', 'Equipo'],
  },
  {
    id: 'cerrar-cuenta',
    category: 'Cuenta y planes',
    title: 'Cerrar cuenta',
    summary:
      'Descarga en PDF o CSV lo que quieras conservar, elimina tu historial desde «Análisis anteriores» y escríbenos con «Contactar con soporte»: cerraremos la cuenta y confirmaremos que no queda ningún dato.',
    tags: ['Cuenta', 'Cierre', 'Datos'],
  },
  {
    id: 'contenido-retencion',
    category: 'Privacidad y datos',
    title: 'Contenido analizado y retención',
    summary:
      'Para generar el informe, el contenido se envía a nuestro proveedor de IA (Mistral AI), que no lo usa para entrenar modelos; a PubMed, Europe PMC, openFDA y CIMA solo llegan los términos de búsqueda de cada afirmación. El análisis se conserva en tu historial hasta que lo eliminas.',
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
      'Comprueba que el archivo sea PDF, TXT o MD y que no supere el tamaño máximo permitido antes de volver a cargarlo.',
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
