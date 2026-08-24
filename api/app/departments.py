"""Działy docelowe — jedno źródło prawdy (twardy enum, reguła krytyczna nr 2)."""

from enum import StrEnum

EMAIL_DOMAIN = "example.com"


class Department(StrEnum):
    HUMAN_RESOURCES = "human-resources"
    KADRY = "kadry"
    HELP_DESK = "help-desk"
    IT = "it"
    OTHER = "other"

    @property
    def email(self) -> str:
        return f"{self.value}@{EMAIL_DOMAIN}"


# Krótkie opisy — celowo zwięzłe: dłuższe opisy pogarszały tool calling
# qwen2.5:3b (patrz docs/etap0-wyniki.md).
DEPARTMENT_DESCRIPTIONS: dict[Department, str] = {
    Department.HUMAN_RESOURCES: "rekrutacja, benefity, onboarding",
    Department.KADRY: "urlopy, L4, zaświadczenia, umowy",
    Department.HELP_DESK: "wsparcie użytkownika, dostępy, hasła, logowanie",
    Department.IT: "awarie sprzętu i systemów, infrastruktura, serwery",
    Department.OTHER: "wszystko inne",
}
