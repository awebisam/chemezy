import requests
import asyncio
from typing import Dict, List, Optional
from app.core.config import settings


class PubChemService:
    """Service for querying the PubChem API to retrieve chemical data."""
    
    def __init__(self):
        self.base_url = settings.pubchem_base_url
        self.timeout = settings.pubchem_timeout
    
    async def get_compound_data(self, compound: str) -> Optional[Dict]:
        """
        Retrieve compound data from PubChem API.
        
        Args:
            compound: Chemical formula or name
            
        Returns:
            Dictionary containing compound properties or None if not found
        """
        try:
            # Run the synchronous request in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_get_compound_data,
                compound
            )
            return result
        except Exception as e:
            print(f"Error fetching data for {compound}: {str(e)}")
            return None
    
    def _sync_get_compound_data(self, compound: str) -> Optional[Dict]:
        """Synchronous method to fetch compound data."""
        try:
            # Try to get compound by formula first, then by name
            urls = [
                f"{self.base_url}/compound/formula/{compound}/property/MolecularFormula,MolecularWeight,HBondDonorCount,HBondAcceptorCount/JSON",
                f"{self.base_url}/compound/name/{compound}/property/MolecularFormula,MolecularWeight,HBondDonorCount,HBondAcceptorCount/JSON"
            ]
            
            for url in urls:
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    if "PropertyTable" in data and "Properties" in data["PropertyTable"]:
                        properties = data["PropertyTable"]["Properties"][0]
                        return {
                            "formula": properties.get("MolecularFormula", compound),
                            "molecular_weight": properties.get("MolecularWeight"),
                            "h_bond_donors": properties.get("HBondDonorCount", 0),
                            "h_bond_acceptors": properties.get("HBondAcceptorCount", 0),
                            "source": "PubChem"
                        }
            
            # If no data found, return basic info
            return {
                "formula": compound,
                "molecular_weight": None,
                "h_bond_donors": 0,
                "h_bond_acceptors": 0,
                "source": "Unknown"
            }
            
        except Exception as e:
            print(f"Sync error fetching data for {compound}: {str(e)}")
            return {
                "formula": compound,
                "molecular_weight": None,
                "h_bond_donors": 0,
                "h_bond_acceptors": 0,
                "source": "Error"
            }
    
    async def get_multiple_compounds_data(self, compounds: List[str]) -> Dict[str, Dict]:
        """
        Retrieve data for multiple compounds concurrently.
        
        Args:
            compounds: List of chemical formulas or names
            
        Returns:
            Dictionary mapping compound names to their data
        """
        tasks = [self.get_compound_data(compound) for compound in compounds]
        results = await asyncio.gather(*tasks)
        
        return {
            compound: result for compound, result in zip(compounds, results)
            if result is not None
        }