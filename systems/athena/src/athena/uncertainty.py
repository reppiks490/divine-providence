from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Uncertainty:
    aleatoric: float
    epistemic: float
    distributional: float
    disagreement: float

    @property
    def aggregate(self) -> float:
        vals = [self.aleatoric, self.epistemic, self.distributional, self.disagreement]
        vals = [min(1.0, max(0.0, float(v))) for v in vals]
        # noisy-OR: one severe uncertainty source can dominate without simple averaging hiding it
        return 1.0 - math.prod(1.0 - v for v in vals)
