import { ApplicationsApiError } from "@/features/applications/api/applications_api";

export function mapStatusUpdateConflictMessage(error: ApplicationsApiError): string | null {
  if (error.status !== 409) {
    return null;
  }

  if (error.code === "INVALID_STATUS_TRANSITION") {
    return "This transition is not allowed for the current application status. Refresh and choose an allowed transition.";
  }

  if (error.code === "VERSION_CONFLICT") {
    return "The application was updated by another process. Refresh and retry with the latest version.";
  }

  return null;
}
