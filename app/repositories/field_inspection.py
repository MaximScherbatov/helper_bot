from sqlalchemy import text
from sqlalchemy.orm import Session


class FieldInspectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_inspector_by_bot_user_id(self, bot_user_id: int) -> dict | None:
        sql = text("""
            SELECT
                ibu.id AS link_id,
                i.id AS inspector_id,
                i.fio,
                i.role,
                i.is_active,
                i.department_id,
                i.unit_id,
                i.position_id
            FROM cm_inspection.cm_inspector_bot_user ibu
            JOIN cm_inspection.cm_inspector i
              ON i.id = ibu.inspector_id
            WHERE ibu.bot_user_id = :bot_user_id
              AND i.is_active = true
            ORDER BY ibu.id ASC
            LIMIT 1
        """)
        row = self.session.execute(sql, {"bot_user_id": bot_user_id}).mappings().first()
        return dict(row) if row else None

    # ---------- Inspector views ----------

    def get_campaigns_for_inspector(self, inspector_id: int) -> list[dict]:
        sql = text("""
            SELECT
                c.id,
                c.name,
                c.description,
                c.date_start,
                c.date_end,
                c.meta,
                COALESCE(ts.total_tasks, 0) AS total_tasks,
                COALESCE(ts.completed_tasks, 0) AS completed_tasks
            FROM cm_inspection.cm_campaign_inspector ci
            JOIN cm_inspection.cm_campaign c ON c.id = ci.campaign_id
            LEFT JOIN (
                SELECT
                    campaign_id,
                    COUNT(*) AS total_tasks,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks
                FROM cm_inspection.cm_task
                GROUP BY campaign_id
            ) ts ON ts.campaign_id = c.id
            WHERE ci.inspector_id = :inspector_id
            ORDER BY c.id DESC
        """)
        rows = self.session.execute(sql, {"inspector_id": inspector_id}).mappings().all()
        return [dict(r) for r in rows]

    def get_tasks_for_inspector(
        self,
        inspector_id: int,
        campaign_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        if campaign_id is None:
            sql = text("""
                SELECT
                    t.id,
                    t.campaign_id,
                    t.object_type,
                    t.object_id,
                    t.object_name,
                    t.address,
                    t.district_name,
                    t.lat,
                    t.lon,
                    t.status,
                    t.planned_date,
                    t.due_date,
                    t.updated_at,
                    t.meta
                FROM cm_inspection.cm_task t
                WHERE t.inspector_id = :inspector_id
                ORDER BY t.id DESC
                LIMIT :limit
            """)
            params = {"inspector_id": inspector_id, "limit": limit}
        else:
            sql = text("""
                SELECT
                    t.id,
                    t.campaign_id,
                    t.object_type,
                    t.object_id,
                    t.object_name,
                    t.address,
                    t.district_name,
                    t.lat,
                    t.lon,
                    t.status,
                    t.planned_date,
                    t.due_date,
                    t.updated_at,
                    t.meta
                FROM cm_inspection.cm_task t
                WHERE t.inspector_id = :inspector_id
                  AND t.campaign_id = :campaign_id
                ORDER BY t.id DESC
                LIMIT :limit
            """)
            params = {"inspector_id": inspector_id, "campaign_id": campaign_id, "limit": limit}

        rows = self.session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]

    def get_campaign_by_id(self, campaign_id: int) -> dict | None:
        sql = text("""
            SELECT
                id, name, description, date_start, date_end,
                min_photos_per_task, max_photos_per_task,
                comment_required,
                checklist_template_id,
                form_template_id,
                instructions_url,
                meta,
                created_at
            FROM cm_inspection.cm_campaign
            WHERE id = :campaign_id
        """)
        row = self.session.execute(sql, {"campaign_id": campaign_id}).mappings().first()
        return dict(row) if row else None

    def get_campaign_stats(self, campaign_id: int) -> dict:
        sql = text("""
            SELECT
                COUNT(*) AS total_tasks,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
                COUNT(*) FILTER (WHERE status = 'assigned') AS assigned_tasks,
                COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress_tasks
            FROM cm_inspection.cm_task
            WHERE campaign_id = :campaign_id
        """)
        row = self.session.execute(sql, {"campaign_id": campaign_id}).mappings().first()
        return dict(row) if row else {
            "total_tasks": 0,
            "completed_tasks": 0,
            "assigned_tasks": 0,
            "in_progress_tasks": 0,
        }

    def get_task_by_id(self, task_id: int) -> dict | None:
        sql = text("""
            SELECT
                id, campaign_id, inspector_id,
                object_type, object_id, object_name,
                address, district_name,
                lat, lon,
                status,
                planned_date, due_date,
                created_at, updated_at,
                meta,
                checklist_completed,
                form_template_id
            FROM cm_inspection.cm_task
            WHERE id = :task_id
        """)
        row = self.session.execute(sql, {"task_id": task_id}).mappings().first()
        return dict(row) if row else None

    def get_inspector_progress(self, inspector_id: int) -> dict:
        sql = text("""
            SELECT
                COUNT(*) AS total_tasks,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
                COUNT(*) FILTER (WHERE status = 'assigned') AS assigned_tasks,
                COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress_tasks
            FROM cm_inspection.cm_task
            WHERE inspector_id = :inspector_id
        """)
        row = self.session.execute(sql, {"inspector_id": inspector_id}).mappings().first()
        return dict(row) if row else {
            "total_tasks": 0,
            "completed_tasks": 0,
            "assigned_tasks": 0,
            "in_progress_tasks": 0,
        }

    # ---------- Curator views (пока просто последние кампании) ----------

    def get_recent_campaigns(self, limit: int = 10) -> list[dict]:
        sql = text("""
            SELECT
                id, name, description, date_start, date_end, meta, created_at
            FROM cm_inspection.cm_campaign
            ORDER BY id DESC
            LIMIT :limit
        """)
        rows = self.session.execute(sql, {"limit": limit}).mappings().all()
        return [dict(r) for r in rows]