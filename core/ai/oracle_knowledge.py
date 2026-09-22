"""
Oracle Fusion Cloud Domain & Environment Knowledge Base
======================================================
Comprehensive knowledge base for Oracle Cloud automated execution, containing domain rules,
navigation maps, demo vs production environment heuristics, client-specific vs demo fallback logic,
and self-healing guidelines.
"""

from typing import Dict, Any, List, Optional
import re

# ==============================================================================
# 1. ORACLE FUSION NAVIGATION TOPOLOGY & HIERARCHY MAP
# ==============================================================================
ORACLE_FUSION_NAV_MAP: Dict[str, Dict[str, Any]] = {
    # Top Tab: "My Team" (Hiring Manager / Line Manager View)
    "my team": {
        "tab_aliases": ["My Team", "Manager Access", "Team Management"],
        "tiles": {
            "hiring": {
                "name": "Hiring",
                "subtabs": ["Requisitions", "Candidate Pools", "Job Offers", "Interviews", "Events", "Campaigns"],
                "quick_actions": ["Create Job Requisition", "Add Candidate", "Review Offers", "View Candidate Applications"]
            },
            "journeys": {
                "name": "Journeys",
                "subtabs": ["My Tasks", "Assigned Journeys", "Explore"],
                "quick_actions": ["Assign Journey", "Track Progress"]
            },
            "team compensation": {
                "name": "Team Compensation",
                "subtabs": ["Salary History", "Individual Compensation", "Total Rewards"],
                "quick_actions": ["Allocate Compensation", "View Balances"]
            },
            "performance": {
                "name": "Performance",
                "subtabs": ["Performance Documents", "Goals", "Check-ins"],
                "quick_actions": ["Set Goals", "Evaluate Worker"]
            },
            "show more": {
                "name": "Show More",
                "description": "Expands hidden tiles under My Team"
            }
        }
    },

    # Top Tab: "Me" (Employee Self-Service)
    "me": {
        "tab_aliases": ["Me", "Self-Service", "Employee Portal"],
        "tiles": {
            "current jobs": {"name": "Current Jobs", "subtabs": ["Search Jobs", "Saved Jobs", "Applications"]},
            "personal details": {"name": "Personal Details", "subtabs": ["Contact Info", "Biographical Info", "Family & Emergency Contacts"]},
            "document records": {"name": "Document Records", "subtabs": ["Add Document", "Issued Documents"]},
            "pay": {"name": "Pay", "subtabs": ["Payslips", "Payment Methods", "Tax Withholding"]}
        }
    },

    # Top Tab: "HR Group" / "My Client Groups" (HR Specialist / Recruiter View)
    "my client groups": {
        "tab_aliases": ["My Client Groups", "HR Group", "Human Resources", "Workforce Management"],
        "tiles": {
            "hiring": {
                "name": "Hiring",
                "subtabs": ["Job Requisitions", "Job Offers", "Candidate Search", "Recruiting Agency", "Candidate Pools"],
                "quick_actions": ["Create Requisition", "Add to Pool", "Create Candidate", "Mass Offer Creation"]
            },
            "employment": {
                "name": "Employment",
                "subtabs": ["Manage Employment", "Change Assignment", "Transfer", "Promote", "Terminate"],
                "quick_actions": ["Hire an Employee", "Add Pending Worker", "Manage Direct Reports"]
            },
            "workforce structures": {
                "name": "Workforce Structures",
                "subtabs": ["Manage Jobs", "Manage Positions", "Manage Locations", "Manage Departments", "Manage Organizations"]
            },
            "show more": {
                "name": "Show More",
                "description": "Expands comprehensive HR administration tasks"
            }
        }
    },

    # Top Tab: "Procurement"
    "procurement": {
        "tab_aliases": ["Procurement", "Purchasing"],
        "tiles": {
            "purchase requisitions": {"name": "Purchase Requisitions", "subtabs": ["Enter Requisition Line", "My Requisitions"]},
            "purchase orders": {"name": "Purchase Orders", "subtabs": ["Manage Orders", "Create Order"]},
            "suppliers": {"name": "Suppliers", "subtabs": ["Manage Suppliers", "Register Supplier"]}
        }
    },

    # Top Tab: "Tools" / "Setup and Maintenance"
    "tools": {
        "tab_aliases": ["Tools", "Configuration", "Administration"],
        "tiles": {
            "scheduled processes": {"name": "Scheduled Processes", "subtabs": ["Schedule New Process", "Process Overview"]},
            "security console": {"name": "Security Console", "subtabs": ["Users", "Roles", "Certificates", "Single Sign-On"]},
            "reports and analytics": {"name": "Reports and Analytics", "subtabs": ["Browse Catalog", "BI Publisher"]}
        }
    }
}


# ==============================================================================
# 2. DEMO INSTANCE ADAPTIVE INTELLIGENCE & CLIENT FALLBACK HEURISTICS
# ==============================================================================
DEMO_INSTANCE_INDICATORS: List[str] = [
    "saasfaprod1", "test", "dev", "stage", "vision", "demo", "oraclecloud.com", "fa-"
]

FALLBACK_ORACLE_DATA: Dict[str, List[str]] = {
    "business_unit": [
        "US1 Business Unit", "Vision Corporation", "Global Business Unit", "UK Business Unit", "Corporate BU"
    ],
    "department": [
        "Human Resources", "Engineering", "Sales", "Finance", "Information Technology", "Marketing", "Consulting"
    ],
    "location": [
        "Redwood City", "New York", "London", "San Francisco", "Austin", "Chicago", "Bangalore", "Singapore"
    ],
    "recruiting_type": [
        "Standard", "Executive", "Campus", "Contingent", "Hourly", "Professional"
    ],
    "legal_employer": [
        "US1 Legal Entity", "Vision US", "Vision Corporation Inc", "Oracle Demo Employer"
    ]
}


# ==============================================================================
# 3. KNOWLEDGE RETRIEVAL HELPER FUNCTIONS
# ==============================================================================
class OracleKnowledgeBase:
    """Provides contextual intelligence for intent parsing, execution, and self-healing."""

    @classmethod
    def is_demo_instance(cls, url: str) -> bool:
        """Determines if the targeted Oracle environment is a Demo / Test / Vision sandbox."""
        if not url:
            return True
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in DEMO_INSTANCE_INDICATORS)

    @classmethod
    def resolve_navigation_route(cls, target_action: str) -> Optional[Dict[str, Any]]:
        """
        Maps high-level business goals (e.g. 'Navigate to Hiring under My Team')
        to exact Oracle Tab Bar + App Tile actions.
        """
        target_norm = target_action.lower()

        # Check explicit tab -> tile patterns
        for tab_key, tab_data in ORACLE_FUSION_NAV_MAP.items():
            for alias in tab_data["tab_aliases"]:
                if alias.lower() in target_norm:
                    for tile_key, tile_data in tab_data["tiles"].items():
                        if tile_key in target_norm or tile_data["name"].lower() in target_norm:
                            return {
                                "tab_name": tab_data["tab_aliases"][0],
                                "tile_name": tile_data["name"],
                                "strategy": "tab_then_tile"
                            }

        # Check standalone tile names
        for tab_key, tab_data in ORACLE_FUSION_NAV_MAP.items():
            for tile_key, tile_data in tab_data["tiles"].items():
                if tile_key in target_norm or tile_data["name"].lower() in target_norm:
                    return {
                        "tab_name": tab_data["tab_aliases"][0],
                        "tile_name": tile_data["name"],
                        "strategy": "tab_then_tile"
                    }

        return None

    @classmethod
    def get_fallback_data(cls, field_name: str, original_val: str) -> Optional[str]:
        """Provides smart fallback suggestions when client-specific data does not exist in demo instance."""
        field_norm = field_name.lower().replace(" ", "_")
        for key, values in FALLBACK_ORACLE_DATA.items():
            if key in field_norm:
                for val in values:
                    if val.lower() != original_val.lower():
                        return val
        return None

    @classmethod
    def generate_expert_system_prompt(cls) -> str:
        """Returns the high-caliber domain knowledge injected into Gemini AI client."""
        return """You are the World's Foremost Oracle Fusion Cloud HCM/ERP/SCM Test Automation Architect.
You understand:
1. Navigation Paradigm:
   - Oracle uses Top Navigation Tabs (e.g. 'Me', 'My Team', 'My Client Groups', 'Procurement', 'Tools').
   - Beneath each Top Tab are Application Tiles (e.g. 'Hiring', 'Journeys', 'Performance', 'Document Records').
   - Deep nested navigation occurs via Left side subtabs ('Requisitions', 'Candidate Pools', 'Offers') or Action Menu buttons ('+ Create', 'Actions', 'Edit', 'Submit').

2. Environment Awareness (Demo vs Production):
   - In Demo/Sandbox pods (e.g., fa-test-saasfaprod1), specific client organizational hierarchy or custom job titles may not be seeded.
   - If an exact client string is unavailable, prioritize UI discovery, seeded demo entities (e.g. 'US1 Business Unit', 'Vision Corporation'), and flexible selection.
   - Never mark test steps as FAILED due to 'custom' action requirements; convert all instructions into concrete, automated browser interactions.

3. ADF & JET Element Locators:
   - Oracle ADF / Oracle JET framework renders dynamic IDs (e.g., `pt1:_FOr1:1:_FONSr2:0:MAnt2:1:pt_r1:0:rt:1:dynam1:0:jobTitle::content`).
   - Never depend on full dynamic ADF IDs. Use semantic aria-labels, placeholder attributes, label-adjacent inputs, and Playwright role locators (`page.get_by_role`, `page.get_by_label`, `page.get_by_text`).
"""
