"""
Módulo de extracción de características geométricas explicables para LSM.
Calcula ángulos articulares inter-falángicos, distancias euclidianas normalizadas,
estado de extensión/flexión de cada dedo y vector normal de orientación de la palma.
"""

import math
from typing import Dict, Any, List, Tuple


def euclidean_distance_3d(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    """Calcula la distancia euclidiana 3D entre dos puntos."""
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


class HandGeometryFeatures:
    """Extrae descriptores morfológicos y cinemáticos a partir de los 21 landmarks de MediaPipe."""

    def __init__(self, landmarks: List[Dict[str, float]]):
        self.raw = landmarks
        self.is_valid = len(landmarks) >= 21
        self.pts: Dict[int, Dict[str, float]] = {}

        if self.is_valid:
            for p in landmarks:
                pid = int(p.get("id", len(self.pts)))
                self.pts[pid] = p

    def get_palm_scale(self) -> float:
        """Distancia de referencia entre la muñeca (0) y el nudillo medio MCP (9)."""
        if not self.is_valid:
            return 1.0
        scale = euclidean_distance_3d(self.pts[0], self.pts[9])
        return scale if scale > 1e-5 else 1.0

    def is_finger_extended(self, finger_name: str) -> bool:
        """
        Determina si un dedo específico está extendido o flexionado.
        Usa la distancia relativa de la punta a la muñeca y el ángulo en la articulación PIP.
        """
        if not self.is_valid:
            return False

        scale = self.get_palm_scale()

        if finger_name == "thumb":
            # Pulgar: distancia TIP(4) a MCP(2) y ángulo CMC(1)-MCP(2)-IP(3)
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

        # Extendido: punta más lejos de la muñeca que la articulación intermedia y ángulo > 140°
        return (d_tip_wrist > d_pip_wrist) and (angle_pip > 135.0)

    def is_finger_curled(self, finger_name: str) -> bool:
        """Determina si un dedo está fuertemente flexionado hacia la palma."""
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

    def get_thumb_index_angle_deg(self) -> float:
        """Ángulo formado entre el pulgar (4), la muñeca (0) y el índice (8)."""
        if not self.is_valid:
            return 0.0
        return angle_between_points_deg(self.pts[4], self.pts[0], self.pts[8])

    def are_fingers_adducted(self) -> bool:
        """Verifica si los 4 dedos (índice a meñique) están juntos y aducidos (como en la seña B)."""
        if not self.is_valid:
            return False

        scale = self.get_palm_scale()
        d_idx_mid = euclidean_distance_3d(self.pts[8], self.pts[12]) / scale
        d_mid_rng = euclidean_distance_3d(self.pts[12], self.pts[16]) / scale
        d_rng_pky = euclidean_distance_3d(self.pts[16], self.pts[20]) / scale

        # Distancia entre puntas adyacentes debe ser pequeña (< 0.35 normalizada)
        return (d_idx_mid < 0.35) and (d_mid_rng < 0.35) and (d_rng_pky < 0.35)

    def is_c_curved(self) -> bool:
        """Verifica curvatura cóncava semicircular de todos los dedos (seña C)."""
        if not self.is_valid:
            return False

        scale = self.get_palm_scale()
        # En la 'C', el ángulo en PIP de los 4 dedos está entre 90° y 140° (ni recto ni puño cerrado)
        ang_idx = angle_between_points_deg(self.pts[5], self.pts[6], self.pts[7])
        ang_mid = angle_between_points_deg(self.pts[9], self.pts[10], self.pts[11])

        # Distancia entre pulgar (4) e índice (8) debe ser apertura intermedia
        d_thumb_idx = euclidean_distance_3d(self.pts[4], self.pts[8]) / scale

        is_mid_curve = (80.0 <= ang_idx <= 145.0) and (80.0 <= ang_mid <= 145.0)
        is_opening_valid = 0.40 <= d_thumb_idx <= 1.40
        return is_mid_curve and is_opening_valid

    def get_palm_normal_z(self) -> float:
        """
        Calcula la componente Z del vector normal a la palma.
        Z negativo indica que la palma apunta frontalmente hacia la cámara.
        """
        if not self.is_valid:
            return 0.0

        p0 = self.pts[0]
        p5 = self.pts[5]
        p17 = self.pts[17]

        # Vectores p0->p5 y p0->p17
        v1 = (p5["x"] - p0["x"], p5["y"] - p0["y"], p5.get("z", 0.0) - p0.get("z", 0.0))
        v2 = (p17["x"] - p0["x"], p17["y"] - p0["y"], p17.get("z", 0.0) - p0.get("z", 0.0))

        # Producto cruz v1 x v2
        nz = v1[0] * v2[1] - v1[1] * v2[0]
        return nz

    def get_hand_center(self) -> Tuple[float, float]:
        """Retorna el centroide (x, y) de la mano en coordenadas normalizadas [0, 1]."""
        if not self.is_valid:
            return (0.5, 0.5)

        avg_x = sum(p["x"] for p in self.pts.values()) / len(self.pts)
        avg_y = sum(p["y"] for p in self.pts.values()) / len(self.pts)
        return (avg_x, avg_y)
