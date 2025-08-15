import os
import sys
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
import ollama
from openai import OpenAI
from typing import Dict, List, Optional, Any
import logging
import json
from datetime import datetime

# --- Logging / encoding fix for Windows consoles (prevents UnicodeEncodeError) ---
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Tools (unchanged except small typing) ---
class ContentResearchTool(BaseTool):
    name: str = "content_research"
    description: str = "Research trending topics and content ideas for specific platforms"

    def _run(self, topic: str, platform: str, industry: str) -> str:
        research_prompt = f"""
        Research trending content ideas for:
        Topic: {topic}
        Platform: {platform}
        Industry: {industry}

        Provide trending hashtags, popular content formats, and engagement strategies.
        """
        return f"Research completed for {topic} on {platform} in {industry} industry"


class ContentGeneratorTool(BaseTool):
    openai_client: Optional[str] = None
    name: str = "content_generator"
    description: str = "Generate platform-specific content based on requirements"

    def __init__(self, ollama_client, openai_client):
        super().__init__()
       
        self.openai_client = openai_client

    def _run(self, content_request: Dict) -> str:
        platform = content_request['target_platform']
        topic = content_request['topic']
        brand_voice = content_request['project']['brand_voice']
        content_type = content_request['content_type']

        platform_specs = {
            'twitter': {'max_length': 280, 'hashtags': 3, 'format': 'concise'},
            'linkedin': {'max_length': 3000, 'hashtags': 5, 'format': 'professional'},
            'facebook': {'max_length': 2000, 'hashtags': 3, 'format': 'engaging'},
            'instagram': {'max_length': 2200, 'hashtags': 15, 'format': 'visual-focused'}
        }

        spec = platform_specs.get(platform, platform_specs['twitter'])

        prompt = f"""
        Create a {content_type} for {platform} about "{topic}".

        Brand Voice: {brand_voice}
        Max Length: {spec['max_length']} characters
        Hashtag Count: {spec['hashtags']}
        Format Style: {spec['format']}

        Requirements:
        - Match the brand voice perfectly
        - Include relevant hashtags
        - Optimize for platform engagement
        - Keep within character limits

        Return as JSON with fields: content, hashtags, platform_optimizations
        """

        try:
            # Use Ollama (Mistral) for content generation
            response = self.ollama_client.chat(
                model='mistral',  # your local ollama model name
                messages=[
                    {'role': 'user', 'content': prompt}
                ]
            )
            # Ollama returns a dict-like response; extract message content safely
            # Accept multiple shapes for robustness
            if isinstance(response, dict):
                # new ollama python clients often return {'message': {'content': '...'}}
                msg = response.get('message') or {}
                if isinstance(msg, dict) and 'content' in msg:
                    return msg['content']
            # fallback: string representation
            return str(response)
        except Exception as e:
            logger.exception("Error generating content via Ollama")
            return json.dumps({
                "content": f"Generated content about {topic} for {platform}",
                "hashtags": ["#content", "#marketing"],
                "platform_optimizations": "Basic optimization applied"
            })


class ContentOptimizerTool(BaseTool):
    name: str = "content_optimizer"
    description: str = "Optimize content for specific platform algorithms and engagement"

    def _run(self, content: str, platform: str, target_audience: str) -> str:
        optimization_strategies = {
            'twitter': [
                'Use compelling opening lines',
                'Include call-to-action',
                'Optimal posting times: 9AM, 3PM EST',
                'Use trending hashtags sparingly'
            ],
            'linkedin': [
                'Professional tone',
                'Include industry insights',
                'Ask questions to drive engagement',
                'Share valuable resources'
            ],
            'facebook': [
                'Emotional storytelling',
                'Use native video when possible',
                'Encourage comments and shares',
                'Post during peak hours: 1-4PM'
            ],
            'instagram': [
                'Visual-first approach',
                'Use all 15 hashtags',
                'Stories for behind-the-scenes',
                'Consistent aesthetic'
            ]
        }

        strategies = optimization_strategies.get(platform, [])
        return f"Applied {len(strategies)} optimization strategies for {platform}"


class ContentTesterTool(BaseTool):
    name: str = "content_tester"
    description: str = "Test and validate content quality and compliance"

    def _run(self, content: str, platform: str, brand_guidelines: Dict) -> str:
        tests = {
            'length_check': len(content) <= self._get_platform_limit(platform),
            'brand_voice_check': self._check_brand_voice(content, brand_guidelines.get('brand_voice', '')),
            'hashtag_check': self._count_hashtags(content) <= self._get_hashtag_limit(platform),
            'compliance_check': self._check_compliance(content, platform)
        }

        passed_tests = sum(tests.values())
        total_tests = len(tests)

        result = {
            'score': (passed_tests / total_tests) * 100,
            'tests_passed': passed_tests,
            'total_tests': total_tests,
            'recommendations': self._generate_recommendations(tests, platform)
        }

        return json.dumps(result)

    def _get_platform_limit(self, platform: str) -> int:
        limits = {'twitter': 280, 'linkedin': 3000, 'facebook': 2000, 'instagram': 2200}
        return limits.get(platform, 280)

    def _get_hashtag_limit(self, platform: str) -> int:
        limits = {'twitter': 3, 'linkedin': 5, 'facebook': 3, 'instagram': 15}
        return limits.get(platform, 3)

    def _check_brand_voice(self, content: str, brand_voice: str) -> bool:
        voice_keywords = {
            'professional': ['expertise', 'solution', 'industry', 'professional'],
            'casual': ['hey', 'awesome', 'cool', 'fun'],
            'friendly': ['welcome', 'happy', 'excited', 'great'],
            'authoritative': ['proven', 'leader', 'expert', 'established']
        }
        keywords = voice_keywords.get(brand_voice.lower(), [])
        return any(keyword in content.lower() for keyword in keywords)

    def _count_hashtags(self, content: str) -> int:
        return content.count('#')

    def _check_compliance(self, content: str, platform: str) -> bool:
        banned_words = ['spam', 'clickbait', 'guaranteed']
        return not any(word in content.lower() for word in banned_words)

    def _generate_recommendations(self, tests: Dict, platform: str) -> List[str]:
        recommendations = []
        if not tests['length_check']:
            recommendations.append(f"Content exceeds {platform} character limit")
        if not tests['brand_voice_check']:
            recommendations.append("Content doesn't match brand voice")
        if not tests['hashtag_check']:
            recommendations.append(f"Too many hashtags for {platform}")
        if not tests['compliance_check']:
            recommendations.append("Content may violate platform guidelines")
        return recommendations


# --- Manager (fixed to normalize CrewOutput) ---
class ContentCrewManager:
    def __init__(self, openai_api_key: str, qdrant_manager, mongodb_manager):
        self.ollama_client = ollama
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.qdrant_manager = qdrant_manager
        self.mongodb_manager = mongodb_manager

        # Initialize tools
        self.content_generator = ContentGeneratorTool(self.ollama_client, self.openai_client)
        self.content_optimizer = ContentOptimizerTool()
        self.content_tester = ContentTesterTool()
        self.content_researcher = ContentResearchTool()

        # Initialize agents
        self._setup_agents()

    def _setup_agents(self):
        self.content_strategist = Agent(
            role="Content Strategist",
            goal="Develop comprehensive content strategies based on project requirements",
            backstory="""You are an expert content strategist...""",
            tools=[self.content_researcher],
            verbose=True
        )

        self.content_creator = Agent(
            role="Content Creator",
            goal="Generate high-quality, platform-specific content that engages audiences",
            backstory="""You are a creative content creator...""",
            tools=[self.content_generator],
            verbose=True
        )

        self.content_optimizer_agent = Agent(
            role="Content Optimizer",
            goal="Optimize content for maximum engagement and platform performance",
            backstory="""You are a social media optimization expert...""",
            tools=[self.content_optimizer],
            verbose=True
        )

        self.qa_agent = Agent(
            role="Quality Assurance Specialist",
            goal="Test and validate content quality, compliance, and brand alignment",
            backstory="""You are a meticulous quality assurance specialist...""",
            tools=[self.content_tester],
            verbose=True
        )

    # --- NEW helper: normalize CrewOutput -> plain text (safe) ---
    def _normalize_crew_output(self, crew_result: Any) -> str:
        """
        Convert CrewOutput (or other structured result) into a single string suitable for
        parsing, embeddings, and saving.
        """
        try:
            # Dynamically import CrewOutput class if available
            from crewai.crews.crew_output import CrewOutput
        except Exception:
            CrewOutput = None

        parts: List[str] = []

        # If it's CrewOutput, iterate tasks_output and collect raw/summary/description
        if CrewOutput and isinstance(crew_result, CrewOutput):
            tasks = getattr(crew_result, "tasks_output", None) or []
            for t in tasks:
                # prefer raw text if available
                raw = getattr(t, "raw", None)
                if isinstance(raw, str) and raw.strip():
                    parts.append(raw.strip())
                    continue
                # otherwise fallback to summary or description
                summary = getattr(t, "summary", None)
                if isinstance(summary, str) and summary.strip():
                    parts.append(summary.strip())
                    continue
                desc = getattr(t, "description", None)
                if isinstance(desc, str) and desc.strip():
                    parts.append(desc.strip())
            # also include top-level raw if exists
            top_raw = getattr(crew_result, "raw", None)
            if isinstance(top_raw, str) and top_raw.strip():
                parts.insert(0, top_raw.strip())
        else:
            # If crew_result is already a string
            if isinstance(crew_result, str):
                parts.append(crew_result.strip())
            else:
                # last resort: convert to string
                parts.append(str(crew_result))

        # Join parts into single text block
        text = "\n\n".join([p for p in parts if p])
        # Trim to a reasonable length for embeddings (optional)
        return text.strip()

    # --- Updated parse to accept normalized text ---
    def _parse_crew_result(self, crew_text: str, content_request: Dict) -> Dict:
        """
        crew_text is guaranteed to be a string (normalized by _normalize_crew_output).
        """
        try:
            if not crew_text:
                return {
                    'content': '',
                    'hashtags': [],
                    'platform': content_request['target_platform'],
                    'content_type': content_request['content_type'],
                    'topic': content_request['topic'],
                    'metadata': {'generated_at': datetime.utcnow().isoformat()}
                }

            # Try JSON
            try:
                if crew_text.lstrip().startswith('{'):
                    parsed = json.loads(crew_text)
                    # ensure 'content' key exists
                    if isinstance(parsed, dict) and 'content' in parsed:
                        parsed.setdefault('platform', content_request['target_platform'])
                        parsed.setdefault('content_type', content_request['content_type'])
                        parsed.setdefault('topic', content_request['topic'])
                        parsed.setdefault('metadata', {'generated_at': datetime.utcnow().isoformat()})
                        return parsed
            except Exception:
                # not JSON — continue
                pass

            # Fallback: simple extraction (lines & hashtags)
            lines = crew_text.splitlines()
            content_lines = []
            hashtags = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # collect hashtags
                if line.startswith('#') or '#' in line:
                    for token in line.split():
                        if token.startswith('#'):
                            hashtags.append(token.strip())
                # skip agent/task markers if present
                if line.lower().startswith('task') or line.lower().startswith('agent'):
                    continue
                content_lines.append(line)

            return {
                'content': '\n'.join(content_lines).strip(),
                'hashtags': list(dict.fromkeys(hashtags)),  # de-duplicate preserving order
                'platform': content_request['target_platform'],
                'content_type': content_request['content_type'],
                'topic': content_request['topic'],
                'metadata': {'generated_at': datetime.utcnow().isoformat()}
            }

        except Exception as e:
            logger.exception("Error parsing crew text")
            return {
                'content': str(crew_text),
                'hashtags': [],
                'platform': content_request['target_platform'],
                'content_type': content_request['content_type'],
                'topic': content_request['topic'],
                'metadata': {'generated_at': datetime.utcnow().isoformat()}
            }

    # --- Main entrypoint (fixed to normalize CrewOutput before embedding/saving) ---
    async def generate_content(self, content_request: Dict) -> Dict:
        """Generate content using the crew of agents"""
        try:
            project = content_request['project']

            # Build tasks (same as before)
            strategy_task = Task(
                description=f"""Develop a content strategy for the topic "{content_request['topic']}" ...""",
                agent=self.content_strategist,
                expected_output="Content strategy with trending topics, hashtags, and recommendations"
            )
            creation_task = Task(
                description=f"""Based on the content strategy, create {content_request['content_type']} ...""",
                agent=self.content_creator,
                expected_output="Platform-specific content with hashtags and optimizations"
            )
            optimization_task = Task(
                description=f"""Optimize the created content for {content_request['target_platform']} ...""",
                agent=self.content_optimizer_agent,
                expected_output="Optimized content with engagement strategies"
            )
            testing_task = Task(
                description=f"""Test the optimized content for quality, compliance, and brand alignment...""",
                agent=self.qa_agent,
                expected_output="Quality assessment report with recommendations"
            )

            crew = Crew(
                agents=[self.content_strategist, self.content_creator,
                        self.content_optimizer_agent, self.qa_agent],
                tasks=[strategy_task, creation_task, optimization_task, testing_task],
                verbose=True
            )

            # kickoff returns a CrewOutput object (structured). Normalize it to text.
            raw_result = crew.kickoff()
            normalized_text = self._normalize_crew_output(raw_result)

            # Parse into structured content_result
            content_result = self._parse_crew_result(normalized_text, content_request)

            # Generate embeddings for the content (pass a string)
            text_for_embedding = content_result.get('content') or normalized_text or content_request.get('topic', '')
            embedding = await self._generate_embedding(text_for_embedding)

            # Store in vector database (ensure serializable content)
            await self.qdrant_manager.add_content_embedding(
                str(project.get('_id') or project.get('id') or 'unknown'),
                text_for_embedding,
                {
                    'platform': content_request['target_platform'],
                    'content_type': content_request['content_type'],
                    'topic': content_request['topic'],
                    'created_at': datetime.utcnow().isoformat()
                },
                embedding
            )

            # Save to MongoDB (only JSON-serializable fields)
            try:
                content_id = self.mongodb_manager.save_content(
                    str(project.get('_id') or project.get('id') or ''),
                    {
                        'content': content_result.get('content'),
                        'platform': content_result.get('platform'),
                        'content_type': content_result.get('content_type'),
                        'hashtags': content_result.get('hashtags', []),
                        'metadata': content_result.get('metadata', {}),
                    }
                )
                content_result['content_id'] = content_id
            except Exception:
                logger.exception("Failed to save content to MongoDB, continuing without content_id")

            # Optionally attach the raw metadata (token usage etc.) as JSON-safe dict
            try:
                # CrewOutput may expose json_dict or token_usage; convert to JSON-safe structure
                meta = {}
                if hasattr(raw_result, "json_dict") and raw_result.json_dict:
                    meta.update(raw_result.json_dict)
                if hasattr(raw_result, "token_usage") and raw_result.token_usage:
                    # attempt to convert token_usage to dict
                    try:
                        meta['token_usage'] = raw_result.token_usage.__dict__
                    except Exception:
                        meta['token_usage'] = str(raw_result.token_usage)
                content_result.setdefault('metadata', {}).update({'crew_meta': meta})
            except Exception:
                logger.debug("Could not extract extra CrewOutput metadata")

            return content_result

        except Exception as e:
            logger.exception(f"Error in content generation crew: {e}")
            raise

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI (ensures input is string)"""
        try:
            if not isinstance(text, str):
                text = str(text)
            # truncate if too long (optional safety)
            if len(text) > 20000:
                text = text[:20000]

            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.exception("Error generating embedding")
            # Return zero vector as fallback
            return [0.0] * 1536
