#!/usr/bin/env python3
"""
Award Templates Seed Script

Creates predefined award templates for the chemistry education platform.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, create_engine, select
from app.core.config import settings
from app.models.award import AwardTemplate, AwardCategory
from app.models.user import User
from app.services.award_template_service import AwardTemplateService

# Award templates configuration
AWARD_TEMPLATES = [
    # Discovery Awards
    {
        "name": "First Discovery",
        "description": "Awarded for discovering your first chemical reaction",
        "category": AwardCategory.DISCOVERY,
        "criteria": {
            "type": "discovery_count",
            "threshold": 1
        },
        "metadata": {
            "icon": "🔬",
            "rarity": "common",
            "points": 10,
            "tiers": [
                {"name": "Novice Explorer", "threshold": 1, "points": 10},
                {"name": "Dedicated Researcher", "threshold": 5, "points": 25},
                {"name": "Discovery Master", "threshold": 10, "points": 50}
            ]
        }
    },
    {
        "name": "Reaction Master",
        "description": "Awarded for discovering multiple unique reactions",
        "category": AwardCategory.DISCOVERY,
        "criteria": {
            "type": "discovery_count",
            "threshold": 5
        },
        "metadata": {
            "icon": "⚗️",
            "rarity": "uncommon",
            "points": 25,
            "tiers": [
                {"name": "Reaction Finder", "threshold": 5, "points": 25},
                {"name": "Reaction Expert", "threshold": 15, "points": 75},
                {"name": "Reaction Legend", "threshold": 30, "points": 150}
            ]
        }
    },
    {
        "name": "Effect Pioneer",
        "description": "Awarded for discovering reactions with unique visual effects",
        "category": AwardCategory.DISCOVERY,
        "criteria": {
            "type": "unique_effects",
            "threshold": 3
        },
        "metadata": {
            "icon": "✨",
            "rarity": "rare",
            "points": 40,
            "tiers": [
                {"name": "Effect Seeker", "threshold": 3, "points": 40},
                {"name": "Visual Virtuoso", "threshold": 8, "points": 100},
                {"name": "Spectacle Specialist", "threshold": 15, "points": 200}
            ]
        }
    },
    {
        "name": "Complex Reaction Discoverer",
        "description": "Awarded for discovering complex multi-step reactions",
        "category": AwardCategory.DISCOVERY,
        "criteria": {
            "type": "reaction_complexity",
            "threshold": 5,
            "conditions": ["multi_step", "catalyst_required"]
        },
        "metadata": {
            "icon": "🧪",
            "rarity": "epic",
            "points": 75,
            "tiers": [
                {"name": "Complexity Novice", "threshold": 5, "points": 75},
                {"name": "Advanced Synthesizer", "threshold": 12, "points": 150},
                {"name": "Master Chemist", "threshold": 25, "points": 300}
            ]
        }
    },
    
    # Database Contribution Awards
    {
        "name": "Data Guardian",
        "description": "Awarded for contributing high-quality data corrections",
        "category": AwardCategory.DATABASE_CONTRIBUTION,
        "criteria": {
            "type": "debug_submissions",
            "threshold": 3
        },
        "metadata": {
            "icon": "🛡️",
            "rarity": "common",
            "points": 15,
            "tiers": [
                {"name": "Data Helper", "threshold": 3, "points": 15},
                {"name": "Quality Contributor", "threshold": 10, "points": 50},
                {"name": "Database Protector", "threshold": 25, "points": 125}
            ]
        }
    },
    {
        "name": "Quality Assurance",
        "description": "Awarded for maintaining high accuracy in data corrections",
        "category": AwardCategory.DATABASE_CONTRIBUTION,
        "criteria": {
            "type": "correction_accuracy",
            "threshold": 0.9,
            "conditions": ["min_submissions:5"]
        },
        "metadata": {
            "icon": "✅",
            "rarity": "uncommon",
            "points": 30,
            "tiers": [
                {"name": "Accurate Contributor", "threshold": 0.9, "points": 30},
                {"name": "Precision Expert", "threshold": 0.95, "points": 60},
                {"name": "Quality Master", "threshold": 0.98, "points": 120}
            ]
        }
    },
    {
        "name": "Debug Hero",
        "description": "Awarded for significant contributions to data quality",
        "category": AwardCategory.DATABASE_CONTRIBUTION,
        "criteria": {
            "type": "data_quality_impact",
            "threshold": 50
        },
        "metadata": {
            "icon": "🦸",
            "rarity": "rare",
            "points": 60,
            "tiers": [
                {"name": "Bug Finder", "threshold": 50, "points": 60},
                {"name": "Quality Champion", "threshold": 150, "points": 150},
                {"name": "Data Superhero", "threshold": 300, "points": 300}
            ]
        }
    },
    
    # Community Awards
    {
        "name": "Profile Complete",
        "description": "Awarded for completing your user profile",
        "category": AwardCategory.COMMUNITY,
        "criteria": {
            "type": "profile_completeness",
            "threshold": 1.0
        },
        "metadata": {
            "icon": "👤",
            "rarity": "common",
            "points": 5,
            "tiers": [
                {"name": "Profile Filled", "threshold": 1.0, "points": 5}
            ]
        }
    },
    {
        "name": "Daily Streak",
        "description": "Awarded for consecutive days of platform usage",
        "category": AwardCategory.COMMUNITY,
        "criteria": {
            "type": "consecutive_days",
            "threshold": 7
        },
        "metadata": {
            "icon": "🔥",
            "rarity": "uncommon",
            "points": 20,
            "tiers": [
                {"name": "Week Warrior", "threshold": 7, "points": 20},
                {"name": "Monthly Master", "threshold": 30, "points": 100},
                {"name": "Dedication Legend", "threshold": 90, "points": 300}
            ]
        }
    },
    {
        "name": "Helpful Member",
        "description": "Awarded for helping other users in the community",
        "category": AwardCategory.COMMUNITY,
        "criteria": {
            "type": "help_others",
            "threshold": 5
        },
        "metadata": {
            "icon": "🤝",
            "rarity": "rare",
            "points": 35,
            "tiers": [
                {"name": "Helper", "threshold": 5, "points": 35},
                {"name": "Mentor", "threshold": 15, "points": 100},
                {"name": "Community Leader", "threshold": 30, "points": 200}
            ]
        }
    },
    
    # Special Awards
    {
        "name": "Beta Tester",
        "description": "Awarded to early platform users who helped test features",
        "category": AwardCategory.SPECIAL,
        "criteria": {
            "type": "special_event",
            "threshold": 1,
            "conditions": ["beta_period"]
        },
        "metadata": {
            "icon": "🏅",
            "rarity": "legendary",
            "points": 100,
            "tiers": [
                {"name": "Beta Pioneer", "threshold": 1, "points": 100}
            ]
        }
    },
    {
        "name": "Chemistry Innovator",
        "description": "Awarded for exceptional contributions to chemistry education",
        "category": AwardCategory.SPECIAL,
        "criteria": {
            "type": "special_recognition",
            "threshold": 1
        },
        "metadata": {
            "icon": "🏆",
            "rarity": "legendary",
            "points": 200,
            "tiers": [
                {"name": "Innovation Badge", "threshold": 1, "points": 200}
            ]
        }
    },
    
    # Achievement Awards
    {
        "name": "Element Master",
        "description": "Awarded for working with many different chemical elements",
        "category": AwardCategory.ACHIEVEMENT,
        "criteria": {
            "type": "unique_elements",
            "threshold": 20
        },
        "metadata": {
            "icon": "🔬",
            "rarity": "uncommon",
            "points": 30,
            "tiers": [
                {"name": "Element Explorer", "threshold": 20, "points": 30},
                {"name": "Periodic Pro", "threshold": 50, "points": 100},
                {"name": "Element Virtuoso", "threshold": 80, "points": 200}
            ]
        }
    },
    {
        "name": "Safety Champion",
        "description": "Awarded for consistent safe laboratory practices",
        "category": AwardCategory.ACHIEVEMENT,
        "criteria": {
            "type": "safety_score",
            "threshold": 0.95
        },
        "metadata": {
            "icon": "🛡️",
            "rarity": "rare",
            "points": 50,
            "tiers": [
                {"name": "Safety Conscious", "threshold": 0.95, "points": 50},
                {"name": "Safety Expert", "threshold": 0.98, "points": 100},
                {"name": "Safety Master", "threshold": 1.0, "points": 150}
            ]
        }
    }
]


async def create_system_user(db: Session) -> User:
    """Create or get the system user for award template creation."""
    system_user = db.exec(select(User).where(User.username == "system")).first()
    
    if not system_user:
        system_user = User(
            username="system",
            email="system@chemezy.com",
            hashed_password="system_hash",  # This should be a proper hash
            is_admin=True,
            is_active=True
        )
        db.add(system_user)
        db.commit()
        db.refresh(system_user)
        print("Created system user")
    
    return system_user


async def seed_award_templates(db: Session):
    """Seed the database with predefined award templates."""
    print("Starting award template seeding...")
    
    # Get or create system user
    system_user = await create_system_user(db)
    
    # Initialize template service
    template_service = AwardTemplateService(db)
    
    created_count = 0
    updated_count = 0
    
    for template_data in AWARD_TEMPLATES:
        try:
            # Check if template already exists
            existing = db.exec(
                select(AwardTemplate).where(AwardTemplate.name == template_data["name"])
            ).first()
            
            if existing:
                print(f"Template '{template_data['name']}' already exists, skipping...")
                continue
            
            # Create new template
            template = await template_service.create_template(
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                criteria=template_data["criteria"],
                metadata=template_data["metadata"],
                created_by=system_user.id
            )
            
            created_count += 1
            print(f"Created template: {template.name}")
            
        except Exception as e:
            print(f"Error creating template '{template_data['name']}': {e}")
            continue
    
    print(f"Seeding complete! Created {created_count} new templates")
    return created_count


async def main():
    """Main function to run the seeding script."""
    try:
        # Create database engine
        engine = create_engine(settings.database_url)
        
        # Create session
        with Session(engine) as db:
            created_count = await seed_award_templates(db)
            print(f"Successfully seeded {created_count} award templates")
            
    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())