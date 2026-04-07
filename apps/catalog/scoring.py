from .choices import NutriScore

NUTRI_SCORE_POINTS = {
    NutriScore.A: 100,
    NutriScore.B: 75,
    NutriScore.C: 50,
    NutriScore.D: 25,
    NutriScore.E: 0,
    NutriScore.UNKNOWN: 50,
}


def calculate_score(
        nutri_score: str,
        is_organic: bool = False,
        additive_score: int = 100,
) -> int:
    """
    Calculates a 0-100 score following Yuka's methodology:
    - 60% nutritional quality (Nutri-Score)
    - 30% additives (second iteration, defaults to 100 until implemented)
    - 10% ecological (organic label)
    """
    nutri_points = NUTRI_SCORE_POINTS.get(nutri_score, 50)
    organic_points = 100 if is_organic else 0

    score = (
            nutri_points * 0.60 +
            additive_score * 0.30 +
            organic_points * 0.10
    )

    return round(score)
