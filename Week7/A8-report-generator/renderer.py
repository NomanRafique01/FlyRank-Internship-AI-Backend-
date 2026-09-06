import os
from datetime import datetime
from typing import Any, Dict
from playwright.async_api import async_playwright


def generate_html(report_data: Dict[str, Any]) -> str:
    today_str = datetime.now().strftime("%B %d, %Y")

    top_products_rows = "".join(
        f"""<tr>
            <td>{idx + 1}</td>
            <td>{p['product']}</td>
            <td class="text-center">{p['count']}</td>
            <td class="text-right">${p['revenue']:,.2f}</td>
        </tr>"""
        for idx, p in enumerate(report_data.get("top_5_products", []))
    )

    all_orders_rows = "".join(
        f"""<tr>
            <td>{o['id']}</td>
            <td>{o['customer']}</td>
            <td>{o['product']}</td>
            <td class="text-right">${o['amount']:,.2f}</td>
            <td class="text-center">{o['created_at']}</td>
        </tr>"""
        for o in report_data.get("all_orders", [])
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sales & Revenue Report</title>
<style>
  @page {{
    size: A4;
    margin: 15mm;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1f2937;
    margin: 0;
    padding: 0;
    font-size: 13px;
    line-height: 1.5;
  }}
  h1 {{
    font-size: 22px;
    margin-bottom: 4px;
    color: #111827;
  }}
  .date {{
    color: #6b7280;
    font-size: 12px;
    margin-bottom: 20px;
  }}
  .summary-cards {{
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
  }}
  .card {{
    flex: 1;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 12px 16px;
    background-color: #f9fafb;
  }}
  .card-label {{
    font-size: 11px;
    text-transform: uppercase;
    color: #6b7280;
    font-weight: 600;
  }}
  .card-value {{
    font-size: 20px;
    font-weight: bold;
    color: #111827;
    margin-top: 4px;
  }}
  h2 {{
    font-size: 15px;
    color: #1f2937;
    margin-top: 20px;
    margin-bottom: 10px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 4px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 12px;
  }}
  /* Critical print CSS: avoid slicing rows and repeat thead on every page */
  thead {{
    display: table-header-group;
  }}
  tr {{
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  th {{
    background-color: #f3f4f6;
    color: #374151;
    font-weight: 600;
    text-align: left;
    padding: 8px 10px;
    border-bottom: 2px solid #d1d5db;
  }}
  td {{
    padding: 6px 10px;
    border-bottom: 1px solid #e5e7eb;
  }}
  .text-right {{
    text-align: right;
  }}
  .text-center {{
    text-align: center;
  }}
</style>
</head>
<body>
  <h1>Executive Sales Report</h1>
  <div class="date">Generated on {today_str}</div>

  <div class="summary-cards">
    <div class="card">
      <div class="card-label">Total Orders</div>
      <div class="card-value">{report_data.get('total_orders', 0):,}</div>
    </div>
    <div class="card">
      <div class="card-label">Total Revenue</div>
      <div class="card-value">${report_data.get('total_revenue', 0.0):,.2f}</div>
    </div>
  </div>

  <h2>Top 5 Products by Revenue</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 40px;">#</th>
        <th>Product</th>
        <th class="text-center" style="width: 100px;">Orders</th>
        <th class="text-right" style="width: 120px;">Revenue</th>
      </tr>
    </thead>
    <tbody>
      {top_products_rows}
    </tbody>
  </table>

  <h2>All Recorded Orders ({len(report_data.get('all_orders', []))} total)</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 50px;">ID</th>
        <th>Customer</th>
        <th>Product</th>
        <th class="text-right" style="width: 100px;">Amount</th>
        <th class="text-center" style="width: 150px;">Date & Time</th>
      </tr>
    </thead>
    <tbody>
      {all_orders_rows}
    </tbody>
  </table>
</body>
</html>
"""


async def render_pdf(html: str, output_path: str = "reports/test.pdf") -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="load")
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
        )
        await browser.close()
    return output_path


if __name__ == "__main__":
    import asyncio
    from report import getReportData

    data = getReportData()
    html_content = generate_html(data)
    pdf_path = asyncio.run(render_pdf(html_content, "reports/test.pdf"))
    print(f"Generated PDF saved to: {pdf_path}")
