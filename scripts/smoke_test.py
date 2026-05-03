from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_observations, load_public_layers, load_survey_sites
from src.geospatial_utils import prepare_sites_with_features
from src.habitat_score import score_sites


def main() -> None:
    layers = load_public_layers()
    observations = load_observations()
    sites = load_survey_sites()

    featured = prepare_sites_with_features(
        sites=sites,
        estuaries=layers["estuaries"],
        coastline=layers["coastline"],
        inlets=layers["inlets"],
    )
    scored = score_sites(featured, "Tarpon", 7)

    assert not observations.empty, "Observations should not be empty."
    assert not scored.empty, "Scored sites should not be empty."
    assert "habitat_score" in scored.columns, "Missing habitat_score column."
    assert scored["priority"].isin({"High", "Medium", "Low"}).all(), "Invalid priority labels."
    print("Smoke test passed: data load, features, and scoring are healthy.")


if __name__ == "__main__":
    main()
