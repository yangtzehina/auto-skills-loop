import requests


class WorkspaceService:
    def sync_project(self, project_id: str) -> dict:
        return requests.get(f"https://api.example.com/projects/{project_id}").json()

    def review_project(self, project_id: str) -> dict:
        return requests.get(f"https://api.example.com/projects/{project_id}/review").json()
