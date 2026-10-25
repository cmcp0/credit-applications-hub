from __future__ import annotations

import uuid
from typing import Any

LOCAL_PASSWORD = "P@ssw0rd123"

ROLE_IDS: dict[str, uuid.UUID] = {
    "customer": uuid.UUID("11111111-1111-1111-1111-111111111111"),
    "operation": uuid.UUID("22222222-2222-2222-2222-222222222222"),
    "admin": uuid.UUID("33333333-3333-3333-3333-333333333333"),
}

PERMISSION_IDS: dict[str, uuid.UUID] = {
    "applications:create": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001"),
    "applications:list_own": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002"),
    "applications:list_all": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0003"),
    "applications:update_customer": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0004"),
    "users:manage_operations": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0005"),
    "workflows:manage": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0006"),
}

LOCAL_USERS: tuple[dict[str, Any], ...] = (
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444441"),
        "email": "customer@example.com",
        "role": "customer",
        "is_active": True,
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444442"),
        "email": "operation@example.com",
        "role": "operation",
        "is_active": True,
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444443"),
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True,
    },
)

# Admin user used as workflow publisher/owner for local fixtures.
FIXTURE_ADMIN_USER_ID = LOCAL_USERS[2]["id"]

WORKFLOW_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "country": "CO",
        "workflow_id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003"),
        "version": 1,
        "statuses": (
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc3001"),
                "code": "PENDING_REVIEW",
                "label": "Pending Review",
                "is_initial": True,
                "is_terminal": False,
                "sort_order": 1,
            },
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc3002"),
                "code": "APPROVED",
                "label": "Approved",
                "is_initial": False,
                "is_terminal": True,
                "sort_order": 2,
            },
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc3003"),
                "code": "REJECTED",
                "label": "Rejected",
                "is_initial": False,
                "is_terminal": True,
                "sort_order": 3,
            },
        ),
        "transitions": (
            ("PENDING_REVIEW", "APPROVED"),
            ("PENDING_REVIEW", "REJECTED"),
        ),
        "webhook_endpoints": (
            {
                "id": uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddd9001"),
                "provider_code": "mock-co-bank",
                "direction": "EGRESS",
                "event_type": "co.banking_data.fetch",
                "method": "GET",
                "url": "{mock_co_provider_url}",
                "secret_ref": "local://providers/mock-co-bank/token",
                "timeout_ms": 3000,
                "active": True,
            },
        ),
        "operations": (
            {
                "id": uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeee3001"),
                "name": "fetch-co-banking-data",
                "sort_order": 1,
                "active": True,
                "sub_operations": (
                    {
                        "id": uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffff3001"),
                        "sort_order": 1,
                        "execution_type": "THIRD_PARTY_HTTP_REQUEST",
                        "target_ref": "webhook_endpoint:dddddddd-dddd-dddd-dddd-dddddddd9001",
                        "input_template": {
                            "country": "CO",
                            "document_type": "CC",
                            "identity_document": "{{ application.identity_document }}",
                        },
                        "output_alias": "co_banking_data",
                        "active": True,
                        "triggers": (
                            {
                                "id": uuid.UUID("12121212-1212-1212-1212-121212123001"),
                                "trigger_type": "TRIGGER_EVENT",
                                "trigger_name": "credit.application.created",
                                "payload_template": {},
                                "condition_expr": None,
                            },
                        ),
                    },
                    {
                        "id": uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffff3002"),
                        "sort_order": 2,
                        "execution_type": "COMMAND_USE_CASE",
                        "target_ref": "applications.rules.evaluate_dti",
                        "input_template": {
                            "country": "CO",
                            "max_dti": 0.45,
                            "debt_field": "co_banking_data.total_debt",
                            "income_field": "application.monthly_income",
                        },
                        "output_alias": "co_dti_result",
                        "active": True,
                        "triggers": (
                            {
                                "id": uuid.UUID("12121212-1212-1212-1212-121212123002"),
                                "trigger_type": "TRIGGER_COMMAND",
                                "trigger_name": "credit.application.evaluate_dti",
                                "payload_template": {},
                                "condition_expr": None,
                            },
                        ),
                    },
                ),
            },
        ),
    },
    {
        "country": "ES",
        "workflow_id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0006"),
        "version": 1,
        "statuses": (
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6001"),
                "code": "PENDING_REVIEW",
                "label": "Pending Review",
                "is_initial": True,
                "is_terminal": False,
                "sort_order": 1,
            },
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6002"),
                "code": "ADDITIONAL_REVIEW",
                "label": "Additional Review",
                "is_initial": False,
                "is_terminal": False,
                "sort_order": 2,
            },
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6003"),
                "code": "APPROVED",
                "label": "Approved",
                "is_initial": False,
                "is_terminal": True,
                "sort_order": 3,
            },
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6004"),
                "code": "REJECTED",
                "label": "Rejected",
                "is_initial": False,
                "is_terminal": True,
                "sort_order": 4,
            },
        ),
        "transitions": (
            ("PENDING_REVIEW", "ADDITIONAL_REVIEW"),
            ("PENDING_REVIEW", "APPROVED"),
            ("PENDING_REVIEW", "REJECTED"),
            ("ADDITIONAL_REVIEW", "APPROVED"),
            ("ADDITIONAL_REVIEW", "REJECTED"),
        ),
        "operations": (
            {
                "id": uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeee6001"),
                "name": "verify-es-dni",
                "sort_order": 1,
                "active": True,
                "sub_operations": (
                    {
                        "id": uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffff6001"),
                        "sort_order": 1,
                        "execution_type": "QUERY_USE_CASE",
                        "target_ref": "documents.es.verify_dni",
                        "input_template": {
                            "country": "ES",
                            "document_type": "DNI",
                            "identity_document": "{{ application.identity_document }}",
                        },
                        "output_alias": "es_document_verification",
                        "active": True,
                        "triggers": (
                            {
                                "id": uuid.UUID("12121212-1212-1212-1212-121212126001"),
                                "trigger_type": "TRIGGER_EVENT",
                                "trigger_name": "credit.application.created",
                                "payload_template": {},
                                "condition_expr": None,
                            },
                        ),
                    },
                ),
            },
            {
                "id": uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeee6002"),
                "name": "apply-es-additional-review-threshold",
                "sort_order": 2,
                "active": True,
                "sub_operations": (
                    {
                        "id": uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffff6002"),
                        "sort_order": 1,
                        "execution_type": "COMMAND_USE_CASE",
                        "target_ref": "applications.rules.es.additional_review",
                        "input_template": {
                            "country": "ES",
                            "amount_threshold": 12000,
                            "status_if_exceeded": "ADDITIONAL_REVIEW",
                        },
                        "output_alias": "es_additional_review_rule",
                        "active": True,
                        "triggers": (
                            {
                                "id": uuid.UUID("12121212-1212-1212-1212-121212126002"),
                                "trigger_type": "TRIGGER_COMMAND",
                                "trigger_name": "credit.application.evaluate_amount_threshold",
                                "payload_template": {},
                                "condition_expr": None,
                            },
                        ),
                    },
                ),
            },
        ),
        "webhook_endpoints": (),
    },
)
