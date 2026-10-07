"""GET /workflows/{workflow_id} route."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from courseagent.api.schemas import WorkflowStateModel

router = APIRouter()


@router.get("/workflows/{workflow_id}", response_model=WorkflowStateModel)
def get_workflow_state(workflow_id: str, request: Request) -> WorkflowStateModel:
    from courseagent.graph.checkpointer import CheckpointerManager, thread_id_for

    cfg = request.app.state.config
    manager = CheckpointerManager(cfg.data_dir)
    try:
        config = {"configurable": {"thread_id": thread_id_for(workflow_id)}}
        state = manager.saver.get_tuple(config)
        if state is None or state.checkpoint is None:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found.")
        channel_values = state.checkpoint.get("channel_values", {})
        return WorkflowStateModel(
            workflow_id=workflow_id,
            active_query=channel_values.get("query", ""),
            interpreted_filters=channel_values.get("interpreted_filters", {}),
            selected_courses=[c.get("course_id") if isinstance(c, dict) else getattr(c, "course_id", None) for c in channel_values.get("retrieved_courses", [])],
            limitations=channel_values.get("limitations", []),
            status="complete" if channel_values.get("status") in ("ok", "not_found", "out_of_scope") else "active",
        )
    finally:
        manager.close()


def register(app) -> None:
    app.include_router(router)
