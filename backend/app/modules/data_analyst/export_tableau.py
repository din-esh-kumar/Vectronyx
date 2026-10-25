# backend/app/modules/data_analyst/export_tableau.py
import io
import xml.etree.ElementTree as ET
import zipfile
from app.modules.data_analyst.schemas import DashboardPlan

def generate_tableau_twbx_archive(plan: DashboardPlan, csv_content: str, filename_base: str = "Vectronyx_Dashboard") -> io.BytesIO:
    """
    Generates a production-ready Tableau Workbook Package (.twbx)
    containing valid XML workbook (.twb) with calculated fields, worksheets,
    and dashboard layout, bundled with Data/dataset.csv.
    """
    buffer = io.BytesIO()

    # Build XML string for Tableau (.twb)
    # Using clean manual XML construction to guarantee valid Tableau DTD attributes
    calculated_fields_xml = ""
    for idx, calc in enumerate(plan.tableau_calculated_fields):
        caption = calc.get("caption", f"Calc_{idx}")
        formula = calc.get("formula", "")
        # Escape XML entities in formulas
        clean_formula = formula.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        calculated_fields_xml += f"""
      <column caption='{caption}' datatype='real' name='[Calculation_{idx}]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='{clean_formula}' />
      </column>"""

    for idx, kpi in enumerate(plan.kpis):
        clean_formula = kpi.formula_tableau.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        calculated_fields_xml += f"""
      <column caption='{kpi.title}' datatype='real' name='[KPI_{idx}]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='{clean_formula}' />
      </column>"""

    # Build worksheets XML
    worksheets_xml = ""
    zones_xml = ""
    total_vis = len(plan.visuals)
    
    for idx, vis in enumerate(plan.visuals):
        sheet_name = f"Sheet_{idx+1}_{vis.title[:20].replace(' ', '_')}"
        worksheets_xml += f"""
  <worksheet name='{sheet_name}'>
    <table>
      <view>
        <datasources>
          <datasource caption='dataset' name='federated.dataset' />
        </datasources>
        <aggregation value='true' />
      </view>
      <style />
      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='Automatic' />
        </pane>
      </panes>
      <rows>[federated.dataset].[{vis.y_axis}]</rows>
      <cols>[federated.dataset].[{vis.x_axis}]</cols>
    </table>
  </worksheet>"""

        zone_y = 150 + ((idx // 2) * 350)
        zone_x = 20 + ((idx % 2) * 620)
        zones_xml += f"""
        <zone h='330' id='{10 + idx}' name='{sheet_name}' w='600' x='{zone_x}' y='{zone_y}' />"""

    dashboard_height = max(800, 200 + ((total_vis + 1) // 2) * 360)

    twb_xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2024.1.0' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <AccessibleZoneTabOrder />
    <DashboardCanScroll />
  </document-format-change-manifest>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
    <datasource caption='dataset' inline='true' name='federated.dataset' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='dataset' name='textscan.1'>
            <connection class='textscan' directory='Data' filename='dataset.csv' />
          </named-connection>
        </named-connections>
      </connection>
      {calculated_fields_xml}
    </datasource>
  </datasources>
  <worksheets>
    {worksheets_xml}
  </worksheets>
  <dashboards>
    <dashboard name='{plan.title[:30]}'>
      <style />
      <size maxheight='{dashboard_height}' maxwidth='1300' minheight='700' minwidth='1000' />
      <zones>
        <zone h='120' id='1' type='title' w='1240' x='20' y='20' />
        {zones_xml}
      </zones>
    </dashboard>
  </dashboards>
  <windows>
    <window class='dashboard' maximized='true' name='{plan.title[:30]}'>
      <viewpoints />
      <active id='-1' />
    </window>
  </windows>
</workbook>"""

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Main Tableau Workbook XML
        z.writestr(f"{filename_base}.twb", twb_xml)

        # 2. Bundled CSV Data source in Data/ folder
        z.writestr("Data/dataset.csv", csv_content)

        # 3. Tableau Setup & Formulas Guide
        guide_text = f"""========================================================================
VECTRONYX AI WORKBENCH — TABLEAU WORKBOOK PACKAGE (.twbx)
========================================================================
Dashboard: {plan.title}
Dataset:   {plan.dataset_name}

HOW TO OPEN:
1. Double-click '{filename_base}.twbx' or open it via Tableau Desktop or Tableau Public.
2. The dataset.csv is already packaged and linked in the Data/ subfolder.

------------------------------------------------------------------------
TABLEAU CALCULATED FIELDS (READY TO USE):
------------------------------------------------------------------------
"""
        for calc in plan.tableau_calculated_fields:
            guide_text += f"\n-- Field: {calc.get('caption')}\nFormula: {calc.get('formula')}\n"

        for kpi in plan.kpis:
            guide_text += f"\n-- KPI: {kpi.title} ({kpi.rationale})\nFormula: {kpi.formula_tableau}\n"

        z.writestr("Tableau_Formulas_Guide.txt", guide_text)

    buffer.seek(0)
    return buffer
