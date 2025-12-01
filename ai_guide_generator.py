"""
AI-powered achievement guide generator
Combines AI generation with caching and fallback strategies
"""

import json
from openrouter_api import openrouter_api
from database import db


class AIGuideGenerator:
    """Generate and manage AI-powered achievement guides"""

    def __init__(self):
        self.ai_api = openrouter_api

    def generate_guide(self, app_id, achievement_name, game_name,
                      achievement_description, global_percent=None, force_regenerate=False):
        """
        Generate or retrieve AI guide for an achievement

        Args:
            app_id: Steam app ID
            achievement_name: Achievement name
            game_name: Game name
            achievement_description: Achievement description
            global_percent: Global unlock percentage
            force_regenerate: Force new AI generation even if cached

        Returns:
            dict: Guide data with success status
        """
        # Check cache first unless force regenerate
        if not force_regenerate:
            cached_guide = db.get_ai_guide(app_id, achievement_name)
            if cached_guide:
                return {
                    'success': True,
                    'guide': self._format_guide_response(cached_guide),
                    'from_cache': True
                }

        # Generate new guide with AI
        try:
            guide_data = self.ai_api.generate_achievement_guide(
                game_name=game_name,
                achievement_name=achievement_name,
                achievement_description=achievement_description,
                global_percent=global_percent
            )

            if not guide_data:
                return {
                    'success': False,
                    'error': 'Failed to generate guide with AI'
                }

            # Save to database
            strategies_json = json.dumps(guide_data.get('strategies', []))
            tips_json = json.dumps(guide_data.get('tips', []))

            db.save_ai_guide(
                app_id=app_id,
                achievement_name=achievement_name,
                game_name=game_name,
                achievement_description=achievement_description,
                guide_content=guide_data.get('summary', ''),
                difficulty_rating=guide_data.get('difficulty_rating'),
                estimated_time=guide_data.get('estimated_time'),
                strategies=strategies_json,
                tips=tips_json
            )

            return {
                'success': True,
                'guide': guide_data,
                'from_cache': False
            }

        except Exception as e:
            print(f"Error generating AI guide: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _format_guide_response(self, cached_guide):
        """Format cached guide for response"""
        try:
            strategies = json.loads(cached_guide.get('strategies', '[]'))
        except (json.JSONDecodeError, TypeError):
            strategies = []

        try:
            tips = json.loads(cached_guide.get('tips', '[]'))
        except (json.JSONDecodeError, TypeError):
            tips = []

        return {
            'summary': cached_guide.get('guide_content', ''),
            'difficulty_rating': cached_guide.get('difficulty_rating'),
            'estimated_time': cached_guide.get('estimated_time'),
            'strategies': strategies,
            'tips': tips,
            'model_used': cached_guide.get('model_used'),
            'generated_at': str(cached_guide.get('generated_at')),
            'views': cached_guide.get('views', 0),
            'rating': cached_guide.get('rating', 0)
        }

    def batch_generate_for_game(self, app_id, game_name, locked_achievements, max_count=5):
        """
        Generate guides for multiple locked achievements in a game

        Args:
            app_id: Steam app ID
            game_name: Game name
            locked_achievements: List of locked achievement dicts
            max_count: Maximum number to generate

        Returns:
            dict: Results with success/failure counts
        """
        results = {
            'success': True,
            'generated': 0,
            'failed': 0,
            'skipped': 0,
            'guides': []
        }

        for ach in locked_achievements[:max_count]:
            # Check if guide already exists
            cached = db.get_ai_guide(app_id, ach.get('name'))
            if cached:
                results['skipped'] += 1
                continue

            # Generate guide
            result = self.generate_guide(
                app_id=app_id,
                achievement_name=ach.get('name'),
                game_name=game_name,
                achievement_description=ach.get('description', ''),
                global_percent=ach.get('global_percent')
            )

            if result.get('success'):
                results['generated'] += 1
                results['guides'].append({
                    'achievement_name': ach.get('name'),
                    'guide': result['guide']
                })
            else:
                results['failed'] += 1

        return results

    def get_rate_limit_status(self):
        """Get current AI API rate limit status"""
        return self.ai_api.get_rate_limit_status()

    def increment_views(self, guide_id):
        """Increment view count for a guide"""
        try:
            db.increment_guide_views(guide_id)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def rate_guide(self, guide_id, rating):
        """Rate a guide (1-5 stars)"""
        try:
            if not (1 <= rating <= 5):
                return {'success': False, 'error': 'Rating must be between 1 and 5'}

            db.rate_ai_guide(guide_id, rating)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Global AI guide generator instance
ai_guide_generator = AIGuideGenerator()
