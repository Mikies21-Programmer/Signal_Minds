# Especificación Lingüística y Geométrica de LSM — Nivel 1 (Señas Estáticas)

**Fecha:** 29 de septiembre de 2026  
**Documento Fuente:** [`03_DOCS/lsm/LSM_LEVEL_1_SPECIFICATION.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/lsm/LSM_LEVEL_1_SPECIFICATION.md)  
**Referencias Oficiales:** Diccionario de Lengua de Señas Mexicana (DIELSEME), CONADIS, Estándar Fonológico Stokoe/Battison para Lenguas de Señas.

---

## 1. Parámetros Constitutivos de la Seña

En Lengua de Señas Mexicana (LSM), toda unidad gestual se compone de cuatro queremas o parámetros formativos:

1. **Configuración de la Mano (Queirema):** Forma que adoptan los dedos (flexión, extensión, curvatura y aducción/abducción).
2. **Orientación de la Palma:** Dirección hacia donde apunta la superficie palmar de la mano (hacia el interlocutor/cámara, hacia el cuerpo, hacia arriba, etc.).
3. **Movimiento (Kinema):** En Nivel 1 (alfabeto manual estático), el movimiento normativo es **nulo o estático** (estabilidad postural en el tiempo).
4. **Ubicación (Toponema):** Zona del espacio de señación donde se articula el signo (en este nivel: espacio neutro torácico frente a la cámara).

---

## 2. Reglas Geométricas Explicables por Seña (Nivel 1)

### Seña 'A'
- **Queirema (Configuración):**
  - Dedos Índice (8), Medio (12), Anular (16) y Meñique (20): Completamente flexionados en puño. Las distancias de las puntas (TIP) a la base de la palma (P0 / MCP) deben ser mínimas (< 0.5 de la escala de la mano).
  - Pulgar (4): Erecto/extendido al costado de los dedos flexionados, con la punta (TIP 4) posicionada adyacente o superpuesta sobre la falange media del índice.
- **Orientación:** Palma orientada frontalmente hacia el interlocutor (cámara).
- **Criterio de Rechazo:** Si el índice, medio, anular o meñique están extendidos, la seña no es 'A'.

### Seña 'B'
- **Queirema (Configuración):**
  - Dedos Índice (8), Medio (12), Anular (16) y Meñique (20): Completamente extendidos y juntos (aducidos, distancia entre puntas consecutivas menor al 25% de la longitud de la palma).
  - Pulgar (4): Flexionado sobre la palma (la punta del pulgar descansa cruzada cerca de la base palmar de los otros dedos).
- **Orientación:** Palma hacia el frente (cámara), dedos apuntando verticalmente hacia arriba.
- **Criterio de Rechazo:** Si los dedos están separados o si el pulgar está extendido lateralmente, la seña no es 'B'.

### Seña 'C'
- **Queirema (Configuración):**
  - Todos los dedos (1-20): En arco semicircular coordinado.
  - El pulgar (4) y las yemas de los otros cuatro dedos (8, 12, 16, 20) mantienen una distancia de apertura intermedia y convexa, simulando la curvatura de la letra 'C'.
- **Orientación:** Palma orientada lateralmente o semi-perfil respecto a la línea visual.
- **Criterio de Rechazo:** Mano cerrada en puño o mano plana extendida.

### Seña 'L'
- **Queirema (Configuración):**
  - Pulgar (4): Completamente extendido horizontalmente o lateralmente.
  - Índice (8): Completamente extendido verticalmente.
  - Ángulo entre Pulgar e Índice: Aproximadamente 90° (rango válido: 65° a 115°).
  - Dedos Medio (12), Anular (16) y Meñique (20): Completamente flexionados hacia la palma.
- **Orientación:** Palma frontal hacia la cámara.
- **Criterio de Rechazo:** Si el medio está extendido o el pulgar cerrado, la seña no es 'L'.

### Seña 'Y'
- **Queirema (Configuración):**
  - Pulgar (4): Completamente extendido lateralmente hacia un extremo.
  - Meñique (20): Completamente extendido lateralmente hacia el extremo opuesto.
  - Dedos Índice (8), Medio (12) y Anular (16): Completamente flexionados en puño cerrado.
- **Orientación:** Palma orientada hacia el frente o neutra.
- **Criterio de Rechazo:** Si el índice o el medio están levantados, o si el meñique está cerrado, la seña no es 'Y'.

---

## 3. Matriz de Landmarks de Referencia (MediaPipe Hands 21 Puntos)

```text
Muñeca: P0
Pulgar:  CMC=P1, MCP=P2, IP=P3,  TIP=P4
Índice:  MCP=P5, PIP=P6, DIP=P7, TIP=P8
Medio:   MCP=P9, PIP=P10, DIP=P11, TIP=P12
Anular:  MCP=P13, PIP=P14, DIP=P15, TIP=P16
Meñique: MCP=P17, PIP=P18, DIP=P19, TIP=P20
```
