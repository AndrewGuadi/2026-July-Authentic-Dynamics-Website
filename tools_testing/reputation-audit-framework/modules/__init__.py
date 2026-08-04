"""Collector module registry.

Add a new collector by implementing :class:`modules.base.OSINTModule` and
registering the class here plus a flag in ``config.yaml``.
"""
from __future__ import annotations

from typing import Dict, Tuple, Type

from modules.amass_module import AmassModule
from modules.base import OSINTModule
from modules.blackbird_module import BlackbirdModule
from modules.exiftool_module import ExifToolModule
from modules.maigret_module import MaigretModule
from modules.recon_ng_module import ReconNGModule
from modules.social_analyzer_module import SocialAnalyzerModule
from modules.spiderfoot_module import SpiderFootModule
from modules.theharvester_module import TheHarvesterModule
from modules.trufflehog_module import TruffleHogModule
from modules.yente_module import YenteModule

MODULE_REGISTRY: Dict[str, Type[OSINTModule]] = {
    MaigretModule.name: MaigretModule,
    BlackbirdModule.name: BlackbirdModule,
    SocialAnalyzerModule.name: SocialAnalyzerModule,
    AmassModule.name: AmassModule,
    SpiderFootModule.name: SpiderFootModule,
    ReconNGModule.name: ReconNGModule,
    TheHarvesterModule.name: TheHarvesterModule,
    ExifToolModule.name: ExifToolModule,
    TruffleHogModule.name: TruffleHogModule,
    YenteModule.name: YenteModule,
}

#: Deterministic execution order (cheap/identity first, heavy last).
MODULE_ORDER: Tuple[str, ...] = (
    "maigret",
    "blackbird",
    "social_analyzer",
    "amass",
    "spiderfoot",
    "recon_ng",
    "theharvester",
    "exiftool",
    "trufflehog",
    "yente",
)

__all__ = ["MODULE_REGISTRY", "MODULE_ORDER", "OSINTModule"]
