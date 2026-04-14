"""
Admin router — Contract §3C and §3D.
Implements:
  GET  /admin/metrics
  GET  /admin/reports
  POST /admin/reports/generate
  GET  /admin/reports/{id}/download
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import asyncpg
import io
import csv
from datetime import datetime, timezone
from core.database import get_db
from auth.dependencies import get_current_admin
from auth.models import TokenData

router = APIRouter()


@router.get("/metrics")
async def get_metrics(
    admin: TokenData = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    GET /admin/metrics — Contract §3C.
    Returns dashboard KPIs and chart data for the AdminDashboard page.
    """
    # ── Total searches ────────────────────────────────────────────────
    total_row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM search_logs")
    total_searches = total_row["cnt"] if total_row else 0

    # ── Active users (distinct users who searched in the last 30 days) ─
    active_row = await conn.fetchrow(
        """
        SELECT COUNT(DISTINCT user_id) AS cnt
        FROM search_logs
        WHERE created_at > NOW() - INTERVAL '30 days'
        """
    )
    active_users = active_row["cnt"] if active_row else 0

    # ── Avg response time ─────────────────────────────────────────────
    perf_row = await conn.fetchrow(
        "SELECT AVG(response_time_ms) AS avg_ms FROM search_logs WHERE response_time_ms IS NOT NULL"
    )
    avg_response_time_ms = round(perf_row["avg_ms"] or 0)

    # ── Error rate ────────────────────────────────────────────────────
    error_row = await conn.fetchrow(
        """
        SELECT
          ROUND(
            100.0 * SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*), 0), 2
          ) AS rate
        FROM search_logs
        WHERE created_at > NOW() - INTERVAL '7 days'
        """
    )
    error_rate_pct = float(error_row["rate"] or 0)

    # ── 7-day search volume ───────────────────────────────────────────
    volume_rows = await conn.fetch(
        """
        SELECT TO_CHAR(DATE_TRUNC('day', created_at), 'Dy') AS label,
               COUNT(*) AS value
        FROM search_logs
        WHERE created_at > NOW() - INTERVAL '7 days'
        GROUP BY 1
        ORDER BY MIN(created_at)
        """
    )
    search_volume_7d = [{"label": r["label"], "value": r["value"]} for r in volume_rows]

    # ── Recent activity ───────────────────────────────────────────────
    activity_rows = await conn.fetch(
        """
        SELECT event, detail, TO_CHAR(created_at, 'HH12:MI AM') AS time
        FROM admin_activity_log
        ORDER BY created_at DESC
        LIMIT 10
        """
    )
    recent_activity = [
        {"event": r["event"], "detail": r["detail"], "time": r["time"]}
        for r in activity_rows
    ]

    return {
        "total_searches": total_searches,
        "active_users": active_users,
        "avg_response_time_ms": avg_response_time_ms,
        "error_rate_pct": error_rate_pct,
        "search_volume_7d": search_volume_7d,
        "recent_activity": recent_activity,
    }


@router.get("/reports")
async def list_reports(
    page: int = 1,
    page_size: int = 10,
    admin: TokenData = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    GET /admin/reports — Contract §3D.
    Returns a paginated list of generated reports.
    """
    offset = (page - 1) * page_size

    rows = await conn.fetch(
        """
        SELECT id, name, created_at::date AS date, status
        FROM admin_reports
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        page_size, offset,
    )
    total_row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM admin_reports")
    total = total_row["cnt"] if total_row else 0

    return {
        "items": [
            {
                "id": r["id"],
                "name": r["name"],
                "date": str(r["date"]),
                "status": r["status"],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/reports/generate")
async def generate_report(
    admin: TokenData = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    POST /admin/reports/generate — Contract §3D.
    Kicks off report generation and inserts a pending row.
    """
    now = datetime.now(timezone.utc)
    report_id = f"REP-{now.strftime('%Y%m%d%H%M%S')}"
    name = f"Search Engagement Report — {now.strftime('%Y-%m-%d')}"

    row = await conn.fetchrow(
        """
        INSERT INTO admin_reports (id, name, status, created_at)
        VALUES ($1, $2, 'Generated', $3)
        RETURNING id, name, status, created_at::date AS date
        """,
        report_id, name, now,
    )

    return {
        "id": row["id"],
        "name": row["name"],
        "date": str(row["date"]),
        "status": row["status"],
    }


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    admin: TokenData = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    GET /admin/reports/{id}/download — Contract §3D.
    Returns a CSV file of search log data for the given report.
    """
    report = await conn.fetchrow(
        "SELECT id, name FROM admin_reports WHERE id = $1", report_id
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    rows = await conn.fetch(
        """
        SELECT user_id, query, status, response_time_ms, created_at
        FROM search_logs
        ORDER BY created_at DESC
        LIMIT 10000
        """
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "query", "status", "response_time_ms", "created_at"])
    for r in rows:
        writer.writerow([r["user_id"], r["query"], r["status"], r["response_time_ms"], r["created_at"]])

    output.seek(0)
    filename = f"{report_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
