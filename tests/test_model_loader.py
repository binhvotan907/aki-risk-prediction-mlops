from app.services.model_loader import model_loader


def test_model_loader_loads_production_artifacts():
    loaded = model_loader.load()

    assert loaded.model is not None
    assert loaded.imputer is not None
    assert loaded.feature_order
    assert loaded.threshold > 0
    assert loaded.model_name == "LightGBM"
