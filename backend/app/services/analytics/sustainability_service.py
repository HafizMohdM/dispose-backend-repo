from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import date
from app.repositories.analytics_repository import AnalyticsRepository
from sqlalchemy import func
from app.models.sustainability import SustainabilityMetric, ESGGoal
from app.models.pickup import Pickup, PickupStatus

class SustainabilityService:
    """
    Handles calculations for environmental impact and ESG goal tracking.
    """

    CO2_SAVED_PER_KG_WASTE = 0.51  # Average KG CO2 saved per KG recycled waste
    WATER_SAVED_PER_KG_PAPER = 26.0 # Liters per KG
    ENERGY_SAVED_PER_KG_METAL = 14.0 # kWh per KG

    @staticmethod
    async def get_sustainability_report(db: Session, org_id: int) -> Dict[str, Any]:
        goals = db.query(ESGGoal).filter(ESGGoal.organization_id == org_id).all()
        # Calculate all-time totals dynamically
        waste_aggregates = db.query(
            Pickup.waste_type,
            func.sum(Pickup.actual_weight)
        ).filter(
            Pickup.organization_id == org_id,
            Pickup.status == PickupStatus.COMPLETED
        ).group_by(Pickup.waste_type).all()

        total_waste = 0.0
        total_co2 = 0.0
        total_water = 0.0
        total_energy = 0.0

        for w_type, w_sum in waste_aggregates:
            w_sum = float(w_sum) if w_sum else 0.0
            total_waste += w_sum
            
            # Safely parse enum or string
            w_str = w_type.value if hasattr(w_type, 'value') else str(w_type)
            impact = SustainabilityService.calculate_impact(w_sum, w_str.upper())
            total_co2 += impact["co2_saved"]
            total_water += impact["water_saved"]
            total_energy += impact["energy_saved"]

        current_metrics = {
            "co2_saved_kg": total_co2,
            "waste_diverted_kg": total_waste,
            "water_saved_liters": total_water,
            "energy_saved_kwh": total_energy
        }

        # Update and return ESG Goals
        goals_response = []
        for g in goals:
            # Auto-update current value based on real-time metrics
            if g.unit == "KG_CO2":
                g.current_value = total_co2
            elif g.unit == "KG_WASTE":
                g.current_value = total_waste
                
            if g.target_value > 0 and g.current_value >= g.target_value and g.status != "COMPLETED":
                g.status = "COMPLETED"
                # Here you could potentially trigger an ESG_GOAL_REACHED event

            goals_response.append({
                "title": g.title,
                "target": g.target_value,
                "current": g.current_value,
                "progress_pct": (g.current_value / g.target_value * 100) if g.target_value > 0 else 0,
                "unit": g.unit,
                "status": g.status
            })

        # Save any updated goal states
        db.commit()

        return {
            "current_metrics": current_metrics,
            "goals": goals_response
        }

    @staticmethod
    def calculate_impact(waste_kg: float, material_type: str) -> Dict[str, float]:
        """
        Utility to calculate environmental savings based on weight and material.
        """
        co2 = waste_kg * SustainabilityService.CO2_SAVED_PER_KG_WASTE
        water = 0.0
        energy = 0.0

        if material_type == "PAPER":
            water = waste_kg * SustainabilityService.WATER_SAVED_PER_KG_PAPER
        elif material_type == "METAL":
            energy = waste_kg * SustainabilityService.ENERGY_SAVED_PER_KG_METAL

        return {
            "co2_saved": co2,
            "water_saved": water,
            "energy_saved": energy
        }
