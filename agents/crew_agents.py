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
import re # Added for regex in _post_process_content

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
        include_media = content_request.get('include_media', False)

        # Enhanced platform specifications with content type support
        platform_specs = {
            'twitter': {
                'max_length': 280, 
                'hashtags': 3, 
                'format': 'concise',
                'content_types': {
                    'post': {'max_length': 280, 'template': 'single_tweet'},
                    'thread': {'max_length': 280, 'template': 'twitter_thread'},
                    'poll': {'max_length': 220, 'template': 'twitter_poll'}  # Less space for poll options
                }
            },
            'linkedin': {
                'max_length': 3000, 
                'hashtags': 5, 
                'format': 'professional',
                'content_types': {
                    'post': {'max_length': 3000, 'template': 'linkedin_post'},
                    'article': {'max_length': 8000, 'template': 'linkedin_article'},
                    'poll': {'max_length': 2800, 'template': 'linkedin_poll'}
                }
            },
            'facebook': {
                'max_length': 2000, 
                'hashtags': 3, 
                'format': 'engaging',
                'content_types': {
                    'post': {'max_length': 2000, 'template': 'facebook_post'},
                    'story': {'max_length': 500, 'template': 'facebook_story'},
                    'poll': {'max_length': 1800, 'template': 'facebook_poll'}
                }
            },
            'instagram': {
                'max_length': 2200, 
                'hashtags': 15, 
                'format': 'visual-focused',
                'content_types': {
                    'post': {'max_length': 2200, 'template': 'instagram_post'},
                    'story': {'max_length': 200, 'template': 'instagram_story'},
                    'reel': {'max_length': 1000, 'template': 'instagram_reel'}
                }
            }
        }

        platform_config = platform_specs.get(platform, platform_specs['twitter'])
        content_config = platform_config['content_types'].get(content_type, 
                                                            {'max_length': platform_config['max_length'], 'template': 'basic'})

        # Get content template and format specifications
        template_type = content_config['template']
        max_length = content_config['max_length']
        
        # Create specific prompts based on content type and platform
        prompt = self._create_content_prompt(
            platform, content_type, topic, brand_voice, 
            max_length, platform_config['hashtags'], 
            platform_config['format'], template_type, include_media
        )

        try:
            # Use Ollama (Mistral) for content generation
            response = self.ollama_client.chat(
                model='mistral',
                messages=[
                    {'role': 'user', 'content': prompt}
                ]
            )
            
            # Extract response content
            if isinstance(response, dict):
                msg = response.get('message') or {}
                if isinstance(msg, dict) and 'content' in msg:
                    generated_content = msg['content']
                else:
                    generated_content = str(response)
            else:
                generated_content = str(response)
            
            # Post-process the content to ensure it meets requirements
            return self._post_process_content(generated_content, platform, content_type, max_length)
            
        except Exception as e:
            logger.exception("Error generating content via Ollama")
            return self._create_fallback_content(topic, platform, content_type, max_length, include_media)

    def _create_content_prompt(self, platform: str, content_type: str, topic: str, 
                             brand_voice: str, max_length: int, hashtag_count: int, 
                             format_style: str, template_type: str, include_media: bool) -> str:
        """Create platform and content-type specific prompts"""
        
        base_requirements = f"""
        CRITICAL REQUIREMENTS:
        - Maximum {max_length} characters total (including hashtags and emojis)
        - Brand voice: {brand_voice}
        - Include exactly {hashtag_count} relevant hashtags
        - Style: {format_style}
        - Topic: {topic}
        """
        
        if include_media:
            base_requirements += "\n- Include media suggestion (image/video description in brackets like [Image: description])"
        
        # Platform and content type specific templates
        if platform == 'twitter':
            if content_type == 'post':
                return f"""{base_requirements}
                
                Create a single engaging tweet about {topic}. 
                Format: [Hook sentence] [Main message] [Call to action] [Hashtags]
                Keep it under {max_length} characters total.
                
                Return ONLY the tweet text, nothing else."""
                
            elif content_type == 'thread':
                return f"""{base_requirements}
                
                Create a Twitter thread about {topic} with 3-5 tweets.
                Each tweet must be under 280 characters.
                Format each tweet as: "Tweet X/Y: [content]"
                Separate tweets with "---"
                
                Thread structure:
                Tweet 1: Hook/Introduction
                Tweet 2-4: Key points/details
                Final tweet: Conclusion/Call to action
                
                Return the complete thread with separators."""
                
            elif content_type == 'poll':
                return f"""{base_requirements}
                
                Create a Twitter poll about {topic}.
                Format:
                [Poll question - max 200 chars]
                
                Poll options:
                • Option 1
                • Option 2  
                • Option 3
                • Option 4
                
                [Additional context if needed]
                [Hashtags]
                
                Total under {max_length} characters."""
        
        elif platform == 'linkedin':
            if content_type == 'post':
                return f"""{base_requirements}
                
                Create a professional LinkedIn post about {topic}.
                Structure:
                [Compelling opening line]
                
                [Main content with insights/value]
                
                [Call to action/question for engagement]
                
                [Hashtags]
                
                Keep under {max_length} characters. Use professional tone."""
                
            elif content_type == 'poll':
                return f"""{base_requirements}
                
                Create a LinkedIn poll about {topic}.
                Format:
                [Context/introduction]
                
                [Poll question]
                
                • Option 1
                • Option 2
                • Option 3
                • Option 4
                
                [Why this matters/call for discussion]
                [Hashtags]"""
        
        elif platform == 'facebook':
            if content_type == 'post':
                return f"""{base_requirements}
                
                Create an engaging Facebook post about {topic}.
                Structure:
                [Attention-grabbing opening]
                
                [Story/details that connect emotionally]
                
                [Value/takeaway]
                
                [Call to action for comments/shares]
                [Hashtags]
                
                Keep under {max_length} characters."""
                
            elif content_type == 'poll':
                return f"""{base_requirements}
                
                Create a Facebook poll about {topic}.
                Format:
                [Engaging introduction]
                
                [Poll question]
                
                React with:
                👍 for Option 1
                ❤️ for Option 2  
                😆 for Option 3
                😮 for Option 4
                
                [Additional context]
                [Hashtags]"""
        
        # Fallback generic prompt
        return f"""{base_requirements}
        
        Create {content_type} content for {platform} about {topic}.
        Keep it under {max_length} characters total.
        Return only the content, nothing else."""

    def _post_process_content(self, content: str, platform: str, content_type: str, max_length: int) -> str:
        """Post-process generated content to ensure it meets requirements"""
        try:
            # Remove any JSON formatting if present
            if content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and 'content' in parsed:
                        content = parsed['content']
                        if 'hashtags' in parsed:
                            hashtags = ' '.join(parsed['hashtags']) if isinstance(parsed['hashtags'], list) else str(parsed['hashtags'])
                            content = f"{content} {hashtags}"
                except:
                    pass
            
            # Remove any markdown formatting
            content = content.replace('**', '').replace('*', '')
            
            # Ensure content fits within character limit
            if len(content) > max_length:
                # Smart truncation - try to preserve hashtags
                hashtag_match = re.findall(r'#\w+', content)
                hashtags = ' '.join(hashtag_match[-3:])  # Keep last 3 hashtags
                
                main_content_limit = max_length - len(hashtags) - 5  # 5 chars buffer
                if main_content_limit > 50:  # Ensure we have reasonable space for content
                    main_content = content[:main_content_limit].rsplit(' ', 1)[0]  # Split at word boundary
                    content = f"{main_content} {hashtags}".strip()
                else:
                    content = content[:max_length]
            
            return content
            
        except Exception as e:
            logger.error(f"Error post-processing content: {e}")
            # Emergency fallback - just truncate
            return content[:max_length] if len(content) > max_length else content

    def _create_fallback_content(self, topic: str, platform: str, content_type: str, max_length: int, include_media: bool) -> str:
        """Create fallback content when AI generation fails"""
        media_text = " [Image: relevant visual]" if include_media else ""
        
        if platform == 'twitter' and content_type == 'thread':
            return f"""Tweet 1/3: Exploring {topic} - why it matters today 🧵{media_text}
---
Tweet 2/3: Key insights about {topic} that everyone should know
---
Tweet 3/3: What's your experience with {topic}? Share your thoughts! #content #discussion"""
        
        elif content_type == 'poll':
            return f"""What's your take on {topic}?{media_text}

• Very important
• Somewhat important  
• Not important
• Need more info

Share your thoughts below! #poll #discussion"""
        
        else:
            base_content = f"Exploring {topic} - insights and thoughts{media_text} #content #discussion"
            return base_content[:max_length] if len(base_content) > max_length else base_content


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
