"""
Módulo de extracción de características geométricas morfológicas explicables para LSM.
Calcula ángulos articulares inter-falángicos, distancias euclidianas normalizadas invariantes a escala,
estado discriminativo de extensión/flexión, aducción, curvatura de arco y separación lateral.
Diseñado para la robustez en pruebas humanas reales de A, B, C, L, Y en Nivel 1.
"""

import math
from collections import deque
from typing import Dict, Any, List, Tuple, Optional


def euclidean_distance_3d(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    """Calcula la distancia euclidiana 3D entre dos landmarks anatómicos."""
    dx = p1["x"] - p2["x"]
    dy = p1["y"] - p2["y"]
    dz = p1.get("z", 0.0) - p2.get("z", 0.0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def angle_between_points_deg(p1: Dict[str, float], p2: Dict[str, float], p3: Dict[str, float]) -> float:
    """
    Calcula el ángulo en grados en el vértice p2 formado por los vectores p2->p1 y p2->p3.
    Rango resultante: [0.0, 180.0].
    """
    v1 = (p1["x"] - p2["x"], p1["y"] - p2["y"], p1.get("z", 0.0) - p2.get("z", 0.0))
    v2 = (p3["x"] - p2["x"], p3["y"] - p2["y"], p3.get("z", 0.0) - p2.get("z", 0.0))

    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)

    if mag1 < 1e-6 or mag2 < 1e-6:
        return 0.0

    cos_val = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cos_val))


def clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Acota un valor numérico en el intervalo cerrado [lo, hi]."""
    return max(lo, min(hi, val))


class HandGeometryFeatures:
    """
    Extrae descriptores morfológicos y cinemáticos a partir de los 21 landmarks de MediaPipe.
    Garantiza invariancia a escala y traslación tomando la muñeca (0) como origen y la distancia
    muñeca-nudillo medio (0->9) como factor métrico de normalización.
    """

    def __init__(self, landmarks: List[Dict[str, float]], handedness: str = "Right"):
        self.raw = landmarks
        self.is_valid = len(landmarks) >= 21
        self.handedness = handedness or "Right"
        self.pts: Dict[int, Dict[str, float]] = {}

        if self.is_valid:
            for p in landmarks:
                pid = int(p.get("id", len(self.pts)))
                self.pts[pid] = p

    def get_palm_scale(self) -> float:
        """Distancia de referencia euclidiana 3D entre la muñeca (0) y el MCP medio (9)."""
        if not self.is_valid:
            return 1.0
        scale = euclidean_distance_3d(self.pts[0], self.pts[9])
        return scale if scale > 1e-5 else 1.0

    def get_palm_center(self) -> Dict[str, float]:
        """Calcula el centroide medio de la palma a partir de la muñeca y los MCPs principales."""
        if not self.is_valid:
            return {"x": 0.5, "y": 0.5, "z": 0.0}
        p0 = self.pts[0]
        p5 = self.pts[5]
        p9 = self.pts[9]
        p17 = self.pts[17]
        return {
            "x": (p0["x"] + p5["x"] + p9["x"] + p17["x"]) / 4.0,
            "y": (p0["y"] + p5["y"] + p9["y"] + p17["y"]) / 4.0,
            "z": (p0.get("z", 0.0) + p5.get("z", 0.0) + p9.get("z", 0.0) + p17.get("z", 0.0)) / 4.0
        }

    # =========================================================================
    # ESTADO GENERAL DE EXTENSIÓN / FLEXIÓN DE DEDOS
    # =========================================================================

    def is_finger_extended(self, finger_name: str) -> bool:
        """
        Determina si un dedo específico está anatómicamente extendido.
        Usa la distancia de la punta a la muñeca comparada con la articulación PIP y el ángulo articular.
        """
        if not self.is_valid:
            return False

        scale = self.get_palm_scale()

        if finger_name == "thumb":
            # Pulgar: distancia TIP(4) a MCP(2) normalizada y ángulo CMC(1)-MCP(2)-IP(3)
            dist_tip_mcp = euclidean_distance_3d(self.pts[4], self.pts[2]) / scale
            angle_mcp = angle_between_points_deg(self.pts[1], self.pts[2], self.pts[3])
            return dist_tip_mcp > 0.65 and angle_mcp > 130.0

        joint_map = {
            "index": (5, 6, 7, 8),
            "middle": (9, 10, 11, 12),
            "ring": (13, 14, 15, 16),
            "pinky": (17, 18, 19, 20)
        }

        mcp_idx, pip_idx, dip_idx, tip_idx = joint_map[finger_name]
        d_tip_wrist = euclidean_distance_3d(self.pts[tip_idx], self.pts[0])
        d_pip_wrist = euclidean_distance_3d(self.pts[pip_idx], self.pts[0])
        angle_pip = angle_between_points_deg(self.pts[mcp_idx], self.pts[pip_idx], self.pts[dip_idx])

        # Extendido: punta más lejana de la muñeca que PIP y ángulo mayor a 135 grados
        return (d_tip_wrist > d_pip_wrist) and (angle_pip > 135.0)

    def is_finger_curled(self, finger_name: str) -> bool:
        """Determina si un dedo está flexionado hacia la palma."""
        return not self.is_finger_extended(finger_name)

    def get_finger_extension_states(self) -> Dict[str, bool]:
        """Retorna el mapa booleano de extensión para los 5 dedos."""
        return {
            "thumb": self.is_finger_extended("thumb"),
            "index": self.is_finger_extended("index"),
            "middle": self.is_finger_extended("middle"),
            "ring": self.is_finger_extended("ring"),
            "pinky": self.is_finger_extended("pinky")
        }

    def get_finger_pip_angle(self, finger_name: str) -> float:
        """Retorna el ángulo articular en grados en la articulación PIP del dedo."""
        if not self.is_valid:
            return 0.0
        joint_map = {
            "index": (5, 6, 7),
            "middle": (9, 10, 11),
            "ring": (13, 14, 15),
            "pinky": (17, 18, 19)
        }
        if finger_name not in joint_map:
            return 0.0
        mcp, pip, dip = joint_map[finger_name]
        return angle_between_points_deg(self.pts[mcp], self.pts[pip], self.pts[dip])

    # =========================================================================
    # CARACTERÍSTICAS DISCRIMINATIVAS PARA 'B'
    # =========================================================================

    def get_thumb_fold_score(self) -> float:
        """
        Puntaje específico de flexión del pulgar cruzado sobre la palma para la seña 'B' [0.0, 1.0].
        Una mano abierta con pulgar extendido produce un score cercano a 0.0.
        Solo cuando el pulgar se cruza firmemente sobre la palma o base de MCPs produce >= 0.80.
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        palm_center = self.get_palm_center()

        # 1. Distancia de la punta del pulgar (4) al centroide de la palma
        d_palm = euclidean_distance_3d(self.pts[4], palm_center) / scale
        s_palm = clamp((0.75 - d_palm) / (0.75 - 0.40))

        # 2. Proximidad a los MCPs centrales (base de los dedos índice/medio/anular)
        d_mcp_mid = euclidean_distance_3d(self.pts[4], self.pts[9]) / scale
        d_mcp_rng = euclidean_distance_3d(self.pts[4], self.pts[13]) / scale
        d_mcps = min(d_mcp_mid, d_mcp_rng)
        s_mcps = clamp((0.70 - d_mcps) / (0.70 - 0.35))

        # 3. Pulgar recogido / no extendido lateralmente
        d_curl = euclidean_distance_3d(self.pts[4], self.pts[2]) / scale
        s_curl = clamp((0.70 - d_curl) / (0.70 - 0.42))

        score = 0.40 * s_palm + 0.35 * s_mcps + 0.25 * s_curl
        return clamp(score)

    def get_finger_adduction_score(self) -> float:
        """
        Evalúa el grado de aducción (dedos juntos) de los 4 dedos extendidos [0.0, 1.0].
        Dedos separados (palma abierta) producen < 0.30; dedos juntos producen > 0.80.
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        d_8_12 = euclidean_distance_3d(self.pts[8], self.pts[12]) / scale
        d_12_16 = euclidean_distance_3d(self.pts[12], self.pts[16]) / scale
        d_16_20 = euclidean_distance_3d(self.pts[16], self.pts[20]) / scale
        mean_gap = (d_8_12 + d_12_16 + d_16_20) / 3.0

        return clamp((0.48 - mean_gap) / (0.48 - 0.22))

    def are_fingers_adducted(self) -> bool:
        """Verifica si los 4 dedos están juntos y aducidos (umbral >= 0.65)."""
        return self.get_finger_adduction_score() >= 0.65

    # =========================================================================
    # CARACTERÍSTICAS DISCRIMINATIVAS PARA 'C'
    # =========================================================================

    def get_c_curvature_score(self) -> float:
        """
        Evalúa la curvatura de arco de los 4 dedos (índice, medio, anular, meñique) [0.0, 1.0].
        En 'C', las articulaciones PIP están en un arco suave (~95° a 140°).
        Dedos completamente rectos (>150°, mano abierta) o cerrados en puño (<75°) son penalizados.
        """
        if not self.is_valid:
            return 0.0

        scores = []
        for f in ["index", "middle", "ring", "pinky"]:
            ang = self.get_finger_pip_angle(f)
            if 90.0 <= ang <= 145.0:
                s = 1.0 - (abs(ang - 118.0) / 40.0) * 0.4
            elif ang > 145.0:
                s = clamp(1.0 - (ang - 145.0) / 25.0)
            else:
                s = clamp(1.0 - (90.0 - ang) / 25.0)
            scores.append(clamp(s))

        return sum(scores) / 4.0

    def get_c_opening_score(self) -> float:
        """
        Evalúa la abertura cóncava entre la punta del pulgar (4) y la punta del índice (8) [0.0, 1.0].
        Rango óptimo para 'C': [0.45, 1.15] normalizado por palm_scale.
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        d_thumb_idx = euclidean_distance_3d(self.pts[4], self.pts[8]) / scale
        dist_score = clamp(1.0 - abs(d_thumb_idx - 0.72) / 0.45)

        # Distancia de la punta del índice a su MCP (evita puño cerrado en la palma)
        d_idx_mcp = euclidean_distance_3d(self.pts[8], self.pts[5]) / scale
        not_fist = clamp((d_idx_mcp - 0.40) / 0.30)

        return 0.70 * dist_score + 0.30 * not_fist

    def get_c_thumb_score(self) -> float:
        """
        Evalúa que el pulgar forme el arco inferior de la letra 'C' [0.0, 1.0].
        El pulgar debe estar separado de la palma y curvado hacia los dedos.
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        palm_center = self.get_palm_center()
        d_thumb_palm = euclidean_distance_3d(self.pts[4], palm_center) / scale

        # Separación adecuada de la palma (no aplastado)
        s_sep = clamp((d_thumb_palm - 0.38) / 0.30)
        ang_thumb = angle_between_points_deg(self.pts[1], self.pts[2], self.pts[3])
        s_curve = clamp(1.0 - abs(ang_thumb - 130.0) / 45.0)

        return 0.60 * s_sep + 0.40 * s_curve

    def get_c_arc_consistency(self) -> float:
        """
        Evalúa la uniformidad del arco semicircular entre los 4 dedos [0.0, 1.0].
        Baja desviación estándar entre ángulos PIP indica un arco consistente.
        """
        if not self.is_valid:
            return 0.0

        angles = [self.get_finger_pip_angle(f) for f in ["index", "middle", "ring", "pinky"]]
        mean_ang = sum(angles) / 4.0
        variance = sum((a - mean_ang)**2 for a in angles) / 4.0
        std = math.sqrt(variance)

        return clamp((35.0 - std) / (35.0 - 12.0))

    def get_c_composite_score(
        self,
        w_curv: float = 0.40,
        w_open: float = 0.25,
        w_thumb: float = 0.20,
        w_arc: float = 0.15
    ) -> float:
        """
        Combina los 4 sub-puntajes de 'C' con pesos ajustables:
        C_score = 0.40 * curvature + 0.25 * opening + 0.20 * thumb + 0.15 * arc_consistency.
        """
        c_curv = self.get_c_curvature_score()
        c_open = self.get_c_opening_score()
        c_th = self.get_c_thumb_score()
        c_arc = self.get_c_arc_consistency()

        return clamp(w_curv * c_curv + w_open * c_open + w_thumb * c_th + w_arc * c_arc)

    def is_c_curved(self) -> bool:
        """Verifica curvatura cóncava semicircular de la seña C (umbral >= 0.70)."""
        return self.get_c_composite_score() >= 0.70

    # =========================================================================
    # CARACTERÍSTICAS DISCRIMINATIVAS PARA 'Y'
    # =========================================================================

    def get_y_thumb_extension_score(self) -> float:
        """Puntaje de extensión lateral del pulgar para 'Y' [0.0, 1.0]."""
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        d_tip_mcp = euclidean_distance_3d(self.pts[4], self.pts[2]) / scale
        ang = angle_between_points_deg(self.pts[1], self.pts[2], self.pts[3])

        s_dist = clamp((d_tip_mcp - 0.45) / 0.22)
        s_ang = clamp((ang - 115.0) / 35.0)

        return 0.60 * s_dist + 0.40 * s_ang

    def get_y_pinky_extension_score(self) -> float:
        """Puntaje de extensión del meñique para 'Y' [0.0, 1.0]."""
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        d_tip_wrist = euclidean_distance_3d(self.pts[20], self.pts[0]) / scale
        d_pip_wrist = euclidean_distance_3d(self.pts[18], self.pts[0]) / scale
        ang = angle_between_points_deg(self.pts[17], self.pts[18], self.pts[19])

        is_far = 1.0 if d_tip_wrist > d_pip_wrist else 0.2
        s_ang = clamp((ang - 110.0) / 40.0)

        return 0.50 * is_far + 0.50 * s_ang

    def get_y_center_flexion_score(self) -> float:
        """
        Puntaje de flexión firme de los 3 dedos centrales (índice, medio, anular) [0.0, 1.0].
        Si alguno de los dedos centrales está extendido, este puntaje se reduce drásticamente.
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        curls = []
        for mcp, pip, dip, tip in [(5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16)]:
            d_tip_wrist = euclidean_distance_3d(self.pts[tip], self.pts[0])
            d_pip_wrist = euclidean_distance_3d(self.pts[pip], self.pts[0])
            ang = angle_between_points_deg(self.pts[mcp], self.pts[pip], self.pts[dip])

            is_curled = 1.0 if (d_tip_wrist <= d_pip_wrist + 0.05 * scale) else 0.0
            ang_curl = clamp((145.0 - ang) / (145.0 - 90.0))
            curls.append(0.50 * is_curled + 0.50 * ang_curl)

        return sum(curls) / 3.0

    def get_y_lateral_separation_score(self) -> float:
        """
        Evalúa que la distancia pulgar-meñique sea significativamente mayor
        que la separación entre los dedos centrales [0.0, 1.0].
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()
        d_thumb_pinky = euclidean_distance_3d(self.pts[4], self.pts[20]) / scale
        d_idx_rng = euclidean_distance_3d(self.pts[8], self.pts[16]) / scale
        ratio = d_thumb_pinky / (d_idx_rng + 0.15)

        s_sep = clamp((d_thumb_pinky - 0.85) / 0.50)
        s_rat = clamp((ratio - 1.3) / 1.2)

        return 0.50 * s_sep + 0.50 * s_rat

    def get_y_composite_score(self) -> float:
        """Puntaje compuesto para 'Y' combinando pulgar, meñique, flexión central y separación."""
        th = self.get_y_thumb_extension_score()
        pk = self.get_y_pinky_extension_score()
        cf = self.get_y_center_flexion_score()
        lat = self.get_y_lateral_separation_score()

        raw = 0.25 * th + 0.25 * pk + 0.30 * cf + 0.20 * lat
        # Puertas duras: si el pulgar o meñique no están extendidos, o los centrales no están doblados
        if pk < 0.55 or th < 0.55 or cf < 0.55:
            raw = min(raw, 0.40)

        return clamp(raw)

    # =========================================================================
    # OTROS DESCRIPTORES CINEMÁTICOS Y DIAGNÓSTICO
    # =========================================================================

    def get_thumb_index_angle_deg(self) -> float:
        """Ángulo en grados entre el pulgar (4), la muñeca (0) y el índice (8)."""
        if not self.is_valid:
            return 0.0
        return angle_between_points_deg(self.pts[4], self.pts[0], self.pts[8])

    def get_palm_normal_z(self) -> float:
        """
        Calcula la componente Z del vector normal a la palma.
        Z negativo indica orientación frontal hacia la cámara.
        """
        if not self.is_valid:
            return 0.0

        p0 = self.pts[0]
        p5 = self.pts[5]
        p17 = self.pts[17]

        v1 = (p5["x"] - p0["x"], p5["y"] - p0["y"], p5.get("z", 0.0) - p0.get("z", 0.0))
        v2 = (p17["x"] - p0["x"], p17["y"] - p0["y"], p17.get("z", 0.0) - p0.get("z", 0.0))

        return v1[0] * v2[1] - v1[1] * v2[0]

    def get_hand_center(self) -> Tuple[float, float]:
        """Retorna el centroide (x, y) de la mano en coordenadas normalizadas [0, 1]."""
        if not self.is_valid:
            return (0.5, 0.5)

        avg_x = sum(p["x"] for p in self.pts.values()) / len(self.pts)
        avg_y = sum(p["y"] for p in self.pts.values()) / len(self.pts)
        return (avg_x, avg_y)

    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Genera el diccionario de telemetría diagnóstica en tiempo real
        para la calibración y monitoreo visual de B, C e Y.
        """
        return {
            "b": {
                "thumb_fold": round(self.get_thumb_fold_score() * 100.0, 1),
                "adduction": round(self.get_finger_adduction_score() * 100.0, 1)
            },
            "c": {
                "curvature": round(self.get_c_curvature_score() * 100.0, 1),
                "opening": round(self.get_c_opening_score() * 100.0, 1),
                "thumb_arc": round(self.get_c_thumb_score() * 100.0, 1),
                "arc_consistency": round(self.get_c_arc_consistency() * 100.0, 1)
            },
            "y": {
                "thumb": round(self.get_y_thumb_extension_score() * 100.0, 1),
                "pinky": round(self.get_y_pinky_extension_score() * 100.0, 1),
                "center_flex": round(self.get_y_center_flexion_score() * 100.0, 1),
                "lateral_sep": round(self.get_y_lateral_separation_score() * 100.0, 1)
            },
            "level_2": {
                "j_base": round(self.get_j_configuration_score() * 100.0, 1),
                "n_base": round(self.get_n_configuration_score() * 100.0, 1),
                "q_base": round(self.get_q_configuration_score() * 100.0, 1),
                "x_hook": round(self.get_x_hook_score() * 100.0, 1),
                "z_base": round(self.get_z_configuration_score() * 100.0, 1)
            }
        }

    # =========================================================================
    # CARACTERÍSTICAS MORFOLÓGICAS DE BASE PARA NIVEL 2 (J, Ñ, Q, X, Z)
    # =========================================================================

    def is_index_hooked(self) -> Tuple[bool, float]:
        """
        Determina si el dedo índice está en postura de 'gancho' para la seña 'X'.
        Un índice recto (>140°) o un índice totalmente cerrado en puño (<60°) se rechaza.
        Postura de gancho óptima: PIP flexionado entre 70° y 125°, punta despegada de la palma.
        """
        if not self.is_valid:
            return (False, 0.0)

        ang_pip = self.get_finger_pip_angle("index")
        scale = self.get_palm_scale()

        # Distancia de la punta del índice a su MCP (nudillo)
        d_tip_mcp = euclidean_distance_3d(self.pts[8], self.pts[5]) / scale

        # En gancho: PIP flexionado pero no pegado a la palma como puño cerrado
        if 65.0 <= ang_pip <= 130.0:
            ang_score = 1.0 - (abs(ang_pip - 95.0) / 35.0) * 0.4
        elif ang_pip > 130.0:
            # Demasiado recto
            ang_score = clamp(1.0 - (ang_pip - 130.0) / 20.0)
        else:
            # Demasiado doblado
            ang_score = clamp(1.0 - (65.0 - ang_pip) / 25.0)

        # Distancia tip a MCP moderada (en puño d < 0.25; en gancho d ~ 0.35..0.65; extendido d > 0.80)
        dist_score = clamp(1.0 - abs(d_tip_mcp - 0.50) / 0.30)

        # Los otros dedos (medio, anular, meñique) deben estar flexionados
        curled_other = sum(1.0 for f in ["middle", "ring", "pinky"] if self.is_finger_curled(f)) / 3.0

        score = clamp(0.45 * ang_score + 0.25 * dist_score + 0.30 * curled_other)
        is_hooked = (55.0 <= ang_pip <= 135.0) and (score >= 0.60) and (curled_other >= 0.66)
        return (is_hooked, round(score, 3))

    def get_x_hook_score(self) -> float:
        """Retorna el score de gancho del índice para X."""
        _, score = self.is_index_hooked()
        return score

    def get_n_configuration_score(self) -> float:
        """
        Evalúa la postura de base 'N' (utilizada para la dinámica de 'Ñ').
        Índice y medio extendidos/inclinados juntos hacia adelante, anular y meñique cerrados.
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()

        # Índice y medio deben tener una extensión similar
        ext_idx = 1.0 if self.is_finger_extended("index") else 0.5
        ext_mid = 1.0 if self.is_finger_extended("middle") else 0.5

        # Índice y medio juntos (aducción)
        d_idx_mid = euclidean_distance_3d(self.pts[8], self.pts[12]) / scale
        s_adduction = clamp((0.40 - d_idx_mid) / (0.40 - 0.15))

        # Anular y meñique firmemente flexionados
        curled_ring = 1.0 if self.is_finger_curled("ring") else 0.0
        curled_pinky = 1.0 if self.is_finger_curled("pinky") else 0.0
        s_curled = 0.5 * curled_ring + 0.5 * curled_pinky

        score = 0.30 * ((ext_idx + ext_mid) / 2.0) + 0.35 * s_adduction + 0.35 * s_curled
        return clamp(score)

    def get_q_configuration_score(self) -> float:
        """
        Evalúa la postura de base para 'Q':
        Índice y pulgar dirigidos hacia abajo, dorso de mano visible, dedos medio, anular y meñique flexionados.
        """
        if not self.is_valid:
            return 0.0

        scale = self.get_palm_scale()

        # Índice orientado hacia abajo: tip_y > mcp_y
        idx_down = 1.0 if self.pts[8]["y"] > self.pts[5]["y"] else 0.4

        # Pulgar orientado hacia abajo / extendido cerca del índice
        d_th_idx = euclidean_distance_3d(self.pts[4], self.pts[8]) / scale
        s_opening = clamp(1.0 - abs(d_th_idx - 0.55) / 0.35)

        # Dedos medio, anular y meñique flexionados
        curled_others = sum(1.0 for f in ["middle", "ring", "pinky"] if self.is_finger_curled(f)) / 3.0

        score = 0.35 * idx_down + 0.30 * s_opening + 0.35 * curled_others
        return clamp(score)

    def get_j_configuration_score(self) -> float:
        """
        Evalúa la postura de base para 'J':
        Meñique claramente extendido, índice, medio y anular cerrados en puño.
        """
        if not self.is_valid:
            return 0.0

        ext = self.get_finger_extension_states()
        pk_score = 1.0 if ext["pinky"] else 0.0

        # Los otros tres dedos deben estar flexionados
        other_curled = sum(1.0 for f in ["index", "middle", "ring"] if not ext[f]) / 3.0

        # Rechazo explícito si índice o medio están extendidos
        if ext["index"] or ext["middle"]:
            return min(0.35, 0.5 * pk_score + 0.5 * other_curled)

        score = 0.55 * pk_score + 0.45 * other_curled
        return clamp(score)

    def get_z_configuration_score(self) -> float:
        """
        Evalúa la postura de base para 'Z':
        Dedo índice extendido (apuntador), medio, anular y meñique cerrados en puño.
        """
        if not self.is_valid:
            return 0.0

        ext = self.get_finger_extension_states()
        idx_score = 1.0 if ext["index"] else 0.0

        # Medio, anular y meñique deben estar flexionados
        other_curled = sum(1.0 for f in ["middle", "ring", "pinky"] if not ext[f]) / 3.0

        # Rechazo explícito si meñique o medio están extendidos
        if ext["pinky"] or ext["middle"]:
            return min(0.35, 0.5 * idx_score + 0.5 * other_curled)

        score = 0.55 * idx_score + 0.45 * other_curled
        return clamp(score)

    def get_hand_orientation_visual(self, orientation_invert: bool = False) -> Dict[str, Any]:
        """
        Calcula la orientación visual de la palma (PALM, BACK, SIDE, UNKNOWN)
        utilizando la heurística experimental de producto cruzado 2D.
        """
        return get_hand_orientation_visual(
            self.raw_landmarks,
            handedness=self.handedness,
            orientation_invert=orientation_invert
        )


# =============================================================================
# ESTIMADOR EXPERIMENTAL DE ORIENTACIÓN VISUAL (PALM / BACK / SIDE / UNKNOWN)
# =============================================================================

class OrientationEstimator:
    """
    Estimador de orientación visual de la palma (PALM, BACK, SIDE, UNKNOWN).
    Implementa una heurística visual geométrica propia basada en el producto cruzado
    2D entre el vector longitudinal de la palma (Muñeca [0] -> MCP Medio [9]) y el
    vector transversal (MCP Índice [5] -> MCP Meñique [17]), correlacionado con la
    lateralidad anatómica (Handedness).

    NOTA METODOLÓGICA EXPLICITA:
    Esta es una heurística experimental propia validada físicamente, NO una capacidad
    oficial de MediaPipe. MediaPipe no provee clasificación nativa de palma/dorso.
    """

    def __init__(self, orientation_invert: bool = False, history_len: int = 5):
        self.orientation_invert = orientation_invert
        self.history: deque = deque(maxlen=history_len)

    def estimate(
        self,
        raw_landmarks: List[Dict[str, Any]],
        handedness: str = "Right",
        orientation_invert: Optional[bool] = None
    ) -> Dict[str, Any]:
        invert = self.orientation_invert if orientation_invert is None else orientation_invert
        res = get_hand_orientation_visual(raw_landmarks, handedness=handedness, orientation_invert=invert)
        self.history.append(res["orientation"])
        return res


def get_hand_orientation_visual(
    raw_landmarks: List[Dict[str, Any]],
    handedness: str = "Right",
    orientation_invert: bool = False
) -> Dict[str, Any]:
    """
    Heurística visual propia experimental para determinar la orientación de la mano.
    Estados posibles: PALM, BACK, SIDE, UNKNOWN.

    NOTA: Heurística propia validada físicamente, NO oficial de MediaPipe.
    """
    if not raw_landmarks or len(raw_landmarks) < 21:
        return {
            "orientation": "UNKNOWN",
            "confidence": 0.0,
            "signed_cross": 0.0,
            "aspect_ratio": 0.0,
            "heuristic": "EXPERIMENTAL_VISUAL_CROSS_PRODUCT"
        }

    pts = {int(p.get("id", idx)): p for idx, p in enumerate(raw_landmarks)}

    # Puntos anatómicos clave:
    # 0: Muñeca (wrist)
    # 5: MCP Índice
    # 9: MCP Medio
    # 17: MCP Meñique
    w = pts[0]
    m_idx = pts[5]
    m_mid = pts[9]
    m_pk = pts[17]

    # Vector longitudinal: Muñeca -> MCP Medio
    ux = m_mid["x"] - w["x"]
    uy = m_mid["y"] - w["y"]

    # Vector transversal: MCP Índice -> MCP Meñique
    vx = m_pk["x"] - m_idx["x"]
    vy = m_pk["y"] - m_idx["y"]

    palm_len = math.sqrt(ux * ux + uy * uy)
    palm_width = math.sqrt(vx * vx + vy * vy)

    if palm_len < 1e-4 or palm_width < 1e-4:
        return {
            "orientation": "UNKNOWN",
            "confidence": 0.0,
            "signed_cross": 0.0,
            "aspect_ratio": 0.0,
            "heuristic": "EXPERIMENTAL_VISUAL_CROSS_PRODUCT"
        }

    # Relación de aspecto del dorso/palma (ancho / largo)
    aspect_ratio = palm_width / palm_len

    # Detección de mano vista de perfil (SIDE):
    # Cuando la mano se ve de lado, el ancho transversal entre MCP 5 y MCP 17 se comprime drásticamente
    if aspect_ratio < 0.28:
        return {
            "orientation": "SIDE",
            "confidence": round(1.0 - (aspect_ratio / 0.28) * 0.4, 3),
            "signed_cross": 0.0,
            "aspect_ratio": round(aspect_ratio, 3),
            "heuristic": "EXPERIMENTAL_VISUAL_CROSS_PRODUCT"
        }

    # Producto cruzado 2D: ux * vy - uy * vx
    cross_2d = (ux * vy) - (uy * vx)

    # Lateralidad (Right vs Left):
    # Para mano derecha estándar, cross_2d positivo indica palma visible
    # Para mano izquierda, la relación geométrica relativa se invierte
    is_right = (handedness.lower() != "left")
    signed_cross = cross_2d if is_right else -cross_2d

    # Normalizar confianza según magnitud relativa
    norm_mag = abs(cross_2d) / (palm_len * palm_width)
    confidence = clamp(norm_mag * 1.5, 0.40, 1.0)

    if signed_cross > 0.002:
        state = "PALM" if not orientation_invert else "BACK"
    elif signed_cross < -0.002:
        state = "BACK" if not orientation_invert else "PALM"
    else:
        state = "SIDE"

    return {
        "orientation": state,
        "confidence": round(confidence, 3),
        "signed_cross": round(signed_cross, 5),
        "aspect_ratio": round(aspect_ratio, 3),
        "heuristic": "EXPERIMENTAL_VISUAL_CROSS_PRODUCT"
    }
