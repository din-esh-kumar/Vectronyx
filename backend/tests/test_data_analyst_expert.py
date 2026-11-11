# backend/tests/test_data_analyst_expert.py
import io
import json
import math
import zipfile
import pandas as pd
from starlette.testclient import TestClient

from app.main import app
from app.modules.data_analyst.profiler import (
    classify_dataframe_roles,
    build_expert_statistical_diagnostics,
    compute_correlations_and_matrix,
    compute_data_quality_audit,
    compute_segment_benchmarks,
)
from app.modules.data_analyst.visual_selector import (
    build_expert_visual_plan,
    compute_visual_series_data_expert,
    validate_and_upgrade_visuals,
)
from app.modules.data_analyst.analyst import (
    _heuristic_fallback_dashboard,
    generate_dossier_markdown,
    profile_dataset,
    resolve_prompt_intent_and_columns,
)
from app.modules.data_analyst.export_powerbi import generate_powerbi_pbip_archive
from app.modules.data_analyst.export_tableau import generate_tableau_twbx_archive
from app.modules.data_analyst.schemas import ChartVisualSpec
import xml.etree.ElementTree as ET

client = TestClient(app)


def _make_books_like_csv(n_rows: int = 45) -> str:
    rows = [
        "isbn13,isbn10,title,authors,categories,language_code,thumbnail,description,published_year,average_rating,num_pages,ratings_count"
    ]
    cats = ["Fiction", "Science Fiction & Fantasy", "Business & Economics", "History & Biography", "Juvenile Fiction", "Philosophy", "Psychology", "Computer Science"]
    langs = ["eng", "eng", "eng", "spa", "fre"]
    for i in range(n_rows):
        isbn13 = 9780000000000 + i
        isbn10 = f"{1000000000 + i}"
        year = "" if i == 3 else str(1990 + (i % 30))
        cat = cats[i % len(cats)]
        lang = langs[i % len(langs)]
        author = f"Author Number {i % 9}"
        # Heavy power-law skew on ratings_count + 1 extreme outlier
        if i == 10:
            rating = 4.92
            pages = 1240
            rcount = 4500000
        elif i == 25:
            rating = 1.85
            pages = 48
            rcount = 12
        else:
            rating = round(3.4 + (i % 12) * 0.11, 2)
            pages = 180 + (i % 15) * 28
            rcount = 150 + (i ** 2) * 35
        rows.append(
            f'{isbn13},{isbn10},"Book Title Variant {i}","{author}","{cat}",{lang},'
            f'"https://example.com/thumb/{i}.jpg","This is a long prose book description paragraph describing themes and characters number {i} in detail.",'
            f'{year},{rating},{pages},{rcount}'
        )
    return "\n".join(rows)


def _assert_no_nan(obj):
    if isinstance(obj, float):
        assert not math.isnan(obj) and not math.isinf(obj), f"Invalid float: {obj}"
    elif isinstance(obj, dict):
        for v in obj.values():
            _assert_no_nan(v)
    elif isinstance(obj, list):
        for v in obj:
            _assert_no_nan(v)


def test_books_semantic_roles_exclude_ids_and_urls_and_detect_float_year():
    csv_text = _make_books_like_csv(45)
    df = pd.read_csv(io.StringIO(csv_text))
    roles = classify_dataframe_roles(df)

    assert roles["isbn13"]["role"] == "identifier"
    assert roles["isbn10"]["role"] == "identifier"
    # language_code is low cardinality categorical, NOT identifier
    assert roles["language_code"]["role"] == "categorical_low"
    # thumbnail & long prose description must be isolated as text_freetext
    assert roles["thumbnail"]["role"] == "text_freetext"
    assert roles["description"]["role"] == "text_freetext"
    # published_year had a missing row -> float64 dtype, still parsed as datetime
    assert roles["published_year"]["role"] == "datetime"
    # average_rating & num_pages are intensive (mean, never % scaled); ratings_count is additive
    assert roles["average_rating"]["role"] == "intensive_metric"
    assert roles["num_pages"]["role"] == "intensive_metric"
    assert roles["ratings_count"]["role"] == "additive_metric"
    assert roles["ratings_count"]["is_rate"] is False

    audit = compute_data_quality_audit(df, roles)
    assert "isbn13" in audit.excluded_id_columns
    assert "isbn10" in audit.excluded_id_columns
    assert "published_year" in audit.temporal_columns


def test_constant_csv_still_marks_explicit_ids_as_identifier():
    row = "1234567890,9781234567890,Constant Book,4.25,150\n"
    const_csv = "isbn10,isbn13,title,rating,pages\n" + (row * 30)
    df = pd.read_csv(io.StringIO(const_csv))
    roles = classify_dataframe_roles(df)
    assert roles["isbn10"]["role"] == "identifier"
    assert roles["isbn13"]["role"] == "identifier"

    target_nums, _, _ = resolve_prompt_intent_and_columns(df, "Analyze ratings and pages", roles=roles)
    assert "isbn10" not in target_nums
    assert "isbn13" not in target_nums


def test_expert_quantiles_correlations_anova_and_isolation_forest():
    csv_text = _make_books_like_csv(45)
    df = pd.read_csv(io.StringIO(csv_text))
    roles = classify_dataframe_roles(df)
    _, _, anomalies = profile_dataset(csv_text, roles=roles, df=df)
    target_nums, target_cats, _ = resolve_prompt_intent_and_columns(
        df, "Evaluate ratings_count, average_rating, and num_pages across categories", roles=roles
    )

    assert "isbn13" not in target_nums
    assert "isbn10" not in target_nums
    assert "thumbnail" not in target_cats
    assert "description" not in target_cats

    diags = build_expert_statistical_diagnostics(df, target_nums, roles)
    assert len(diags) >= 3
    for d in diags:
        assert d.metric_name not in ("isbn13", "isbn10")
        assert d.median is not None
        assert d.p25 is not None and d.p75 is not None and d.p95 is not None
        assert d.iqr is not None
        assert d.normality_verdict is not None

    corrs, matrix = compute_correlations_and_matrix(df, target_nums, roles)
    assert len(corrs) >= 1
    assert matrix is not None
    assert "isbn13" not in matrix.metrics
    assert len(matrix.matrix) == len(matrix.metrics)

    benchmarks = compute_segment_benchmarks(df, target_cats, target_nums, roles)
    assert len(benchmarks) >= 1
    assert 0.0 <= benchmarks[0].eta_squared <= 1.0
    assert len(benchmarks[0].rows) >= 2

    # IsolationForest outlier features exist and exclude IDs in explanation
    assert len(anomalies) >= 1
    assert "isbn13" not in anomalies[0].explanation


def test_chart_selection_rules_and_peer_review_upgrades():
    csv_text = _make_books_like_csv(45)
    df = pd.read_csv(io.StringIO(csv_text))
    roles = classify_dataframe_roles(df)
    target_nums, target_cats, intent = resolve_prompt_intent_and_columns(
        df, "Pareto concentration and distribution analysis of ratings_count across categories", roles=roles
    )

    corrs, _ = compute_correlations_and_matrix(df, target_nums, roles)
    expert_visuals = build_expert_visual_plan(
        df=df,
        roles=roles,
        target_numerics=target_nums,
        target_cats=target_cats,
        intent=intent,
        correlations=corrs,
    )
    chart_types = {v.chart_type for v in expert_visuals}
    # Must include distribution histogram, scatter, chronological time-series, and pareto/horizontal bar
    assert "histogram" in chart_types
    assert "scatter" in chart_types
    assert "area" in chart_types  # from published_year datetime
    assert any(ct in chart_types for ct in ("pareto", "horizontal_bar", "bar"))

    for vis in expert_visuals:
        series = compute_visual_series_data_expert(df, vis, roles=roles)
        assert len(series) > 0, f"Empty series for {vis.title}"
        assert vis.selection_reason
        if vis.chart_type == "area" and vis.x_axis == "published_year":
            # Chronological ascending check
            years = [int(pt["name"]) for pt in series]
            assert years == sorted(years)

    # Now peer-review deliberately bad LLM charts:
    bad_proposals = [
        # 1) Line chart on unordered discrete category -> must upgrade to horizontal_bar or bar
        ChartVisualSpec(
            id="bad_line",
            title="Bad Line on Categories",
            chart_type="line",
            x_axis="categories",
            y_axis="ratings_count",
            aggregation="sum",
            description="Bad discrete line",
        ),
        # 2) Pie chart on average_rating (>5 categories and intensive mean) -> must upgrade away from pie
        ChartVisualSpec(
            id="bad_pie",
            title="Bad Pie on Rating",
            chart_type="pie",
            x_axis="categories",
            y_axis="average_rating",
            aggregation="sum",
            description="Bad pie on avg",
        ),
        # 3) Chart using identifier column -> must be dropped
        ChartVisualSpec(
            id="bad_id",
            title="Bad ISBN Chart",
            chart_type="bar",
            x_axis="categories",
            y_axis="isbn13",
            aggregation="sum",
            description="Bad ID sum",
        ),
        # 4) Degenerate scatter with x == y -> must become histogram
        ChartVisualSpec(
            id="bad_scatter",
            title="Self Scatter",
            chart_type="scatter",
            x_axis="num_pages",
            y_axis="num_pages",
            aggregation="raw",
            description="Degenerate self scatter",
        ),
    ]

    repaired = validate_and_upgrade_visuals(
        df=df,
        proposed_visuals=bad_proposals,
        roles=roles,
        target_numerics=target_nums,
        target_cats=target_cats,
        intent=intent,
        correlations=corrs,
    )
    titles_by_id = {v.id: v for v in repaired}
    assert "bad_id" not in titles_by_id
    assert titles_by_id["bad_line"].chart_type in ("bar", "horizontal_bar")
    assert titles_by_id["bad_pie"].chart_type in ("bar", "horizontal_bar")
    assert titles_by_id["bad_pie"].aggregation == "avg"
    assert titles_by_id["bad_scatter"].chart_type == "histogram"


def test_full_pipeline_books_dataset_e2e_and_powerbi_mappings():
    csv_text = _make_books_like_csv(45)
    resp = client.post(
        "/api/analyst/generate-dashboard",
        files={"file": ("Publisher's_Books.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
        data={
            "prompt": "Analyze book ratings, page distributions, and category concentration",
            "dataset_name": "Publisher's_Books.csv",
        },
    )
    assert resp.status_code == 200
    plan_json = resp.json()
    _assert_no_nan(plan_json)

    assert "isbn13" not in plan_json["focused_metrics"]
    assert "isbn10" not in plan_json["focused_metrics"]
    dossier = plan_json["dossier"]
    assert dossier["data_quality_audit"] is not None
    assert "isbn13" in dossier["data_quality_audit"]["excluded_id_columns"]
    assert len(dossier["correlation_insights"]) >= 1
    assert dossier["correlation_matrix"] is not None
    assert len(dossier["segment_benchmarks"]) >= 1

    # Verify Power BI export maps new chart types & escapes apostrophes cleanly
    df = pd.read_csv(io.StringIO(csv_text))
    plan_obj = _heuristic_fallback_dashboard(df, "Analyze ratings and category Pareto concentration", "Publisher's_Books.csv")
    pbip_buf = generate_powerbi_pbip_archive(plan_obj, csv_text, "Publishers_Books")
    with zipfile.ZipFile(pbip_buf, "r") as z:
        assert z.testzip() is None
        report_json = json.loads(z.read("Publishers_Books.Report/report.json").decode("utf-8"))
        visual_types = set()
        for vc in report_json["sections"][0]["visualContainers"]:
            cfg = json.loads(vc["config"])
            vt = cfg["singleVisual"]["visualType"]
            visual_types.add(vt)
        assert "card" in visual_types
        # Should include Power BI mappings beyond basic column chart
        assert any(vt in visual_types for vt in ("scatterChart", "clusteredBarChart", "lineClusteredColumnComboChart", "areaChart"))

    # Verify Tableau export generates well-formed XML even with apostrophes/quotes
    twbx_buf = generate_tableau_twbx_archive(plan_obj, csv_text, "Publishers_Books")
    with zipfile.ZipFile(twbx_buf, "r") as z:
        assert z.testzip() is None
        twb_xml = z.read("Publishers_Books.twb").decode("utf-8")
        root = ET.fromstring(twb_xml)
        assert root.tag == "workbook"

    # Verify Markdown report renders all senior sections
    md = generate_dossier_markdown(plan_obj)
    assert "DATA GOVERNANCE & SCHEMA ROLE AUDIT" in md
    assert "ECONOMETRIC DISTRIBUTION & QUANTILE DIAGNOSTICS" in md
    assert "MULTIVARIATE CORRELATION & FEATURE DRIVER ANALYSIS" in md
    assert "COHORT PERFORMANCE & ANOVA VARIANCE BENCHMARKS" in md
    assert "GOVERNANCE & RISK MITIGATION MATRIX" in md
    assert "METHODOLOGICAL DISCLOSURES" in md
