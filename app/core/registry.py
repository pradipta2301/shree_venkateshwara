from app.collectors.gem import GeMCollector
from app.collectors.odisha_districts import OdishaDistrictCollector
from app.collectors.ocac_collector import OCACCollector
from app.collectors.tendersodisha_collector import TendersOdishaCollector
from app.collectors.odisha_portal_collector import OdishaPortalCollector
from app.collectors.urban_transport_collector import UrbanTransportCollector
from app.collectors.omtes_collector import OMTESCollector
from app.collectors.osic_collector import OSICCollector
from app.collectors.stsc_collector import STSCCollector


class CollectorRegistry:
    def __init__(self):
        self._collectors = {}

    def register(self, name: str, collector_class, collector_type: str = "standard"):
        """
        collector_type can be 'standard' (gem, ocac, nic, portal, urban, omtes, osic)
        or 'district' (requires 1st page OCR pre-filtering, e.g., districts, stsc).
        """
        self._collectors[name] = {
            "class": collector_class,
            "type": collector_type
        }

    def get_collector_info(self, name: str):
        return self._collectors.get(name)

    def get_all_collectors(self):
        return self._collectors


registry = CollectorRegistry()

# Auto-register all active collectors
registry.register("gem", GeMCollector, collector_type="standard")
registry.register("districts", OdishaDistrictCollector, collector_type="district")
registry.register("ocac", OCACCollector, collector_type="standard")
registry.register("tenders_odisha", TendersOdishaCollector, collector_type="standard")
registry.register("odisha_portal", OdishaPortalCollector, collector_type="standard")
registry.register("urban_transport", UrbanTransportCollector, collector_type="standard")
registry.register("omtes", OMTESCollector, collector_type="standard")
registry.register("osic", OSICCollector, collector_type="standard")
registry.register("stsc", STSCCollector, collector_type="district")