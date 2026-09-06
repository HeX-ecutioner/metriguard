"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Codified Rules Registry.
Exports the 6 verified prototype rules for retail commodity packaging.
"""

from typing import List
from app.services.rules.base import RegulatoryRule
from app.services.rules.lmr_2011.r06_1_e_mrp import MRPDeclarationRule
from app.services.rules.lmr_2011.r06_1_c_net_qty import NetQuantityDeclarationRule
from app.services.rules.lmr_2011.r06_1_a_entity import ManufacturerPackerImporterRule
from app.services.rules.lmr_2011.r06_1_d_date import ManufacturePackingDateRule
from app.services.rules.lmr_2011.r06_1_g_consumer import ConsumerCareRule
from app.services.rules.lmr_2011.r06_11_usp import UnitSalePriceRule


def get_lmr_2011_prototype_rules() -> List[RegulatoryRule]:
    """Returns instances of the 6 foundational prototype rules."""
    return [
        MRPDeclarationRule(),
        NetQuantityDeclarationRule(),
        ManufacturerPackerImporterRule(),
        ManufacturePackingDateRule(),
        ConsumerCareRule(),
        UnitSalePriceRule(),
    ]


__all__ = [
    "MRPDeclarationRule",
    "NetQuantityDeclarationRule",
    "ManufacturerPackerImporterRule",
    "ManufacturePackingDateRule",
    "ConsumerCareRule",
    "UnitSalePriceRule",
    "get_lmr_2011_prototype_rules",
]
