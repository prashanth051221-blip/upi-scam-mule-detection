"""Template context shared by every page: which dataset is loaded and the alert rule."""

from . import services


def current_dataset(request):
    key = request.session.get("dataset", "")
    cfg = {**services.DEFAULT_SETTINGS, **request.session.get("settings", {})}
    if cfg["mode"] == "capacity":
        rule = f"Top {cfg['capacity']:g}% of payments"
    else:
        rule = f"Cost-based, ₹{int(cfg['review_cost']):,} per review"
    return {
        "dataset_key": key,
        "dataset_label": services.dataset_label(key, request.session.get("upload_name", "")) if key else "",
        "alert_cfg": cfg,
        "alert_rule": rule,
        "cost_choices": services.COST_CHOICES,
        "nav": request.resolver_match.url_name if request.resolver_match else "",
    }
