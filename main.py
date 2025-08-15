import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional
import uuid

# Load environment variables
load_dotenv()

# Import our custom modules
from database.mongodb_manager import MongoDBManager
from database.qdrant_manager import QdrantManager
from agents.crew_agents import ContentCrewManager
from services.social_media_service import SocialMediaService
from services.scheduler_service import SchedulerService
from mcp.mcp_server import MCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Enable async support
app.config['ASYNC_MODE'] = True

# Initialize services
mongodb_manager = MongoDBManager()
qdrant_manager = QdrantManager()
social_media_service = SocialMediaService()
scheduler_service = SchedulerService()
mcp_server = MCPServer()

# Initialize CrewAI agents
crew_manager = ContentCrewManager(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    qdrant_manager=qdrant_manager,
    mongodb_manager=mongodb_manager
)

# HTML Templates
PROJECT_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Content Generation System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .form-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, select { width: 100%; padding: 8px; margin-bottom: 10px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .project-card { border: 1px solid #ddd; padding: 20px; margin: 20px 0; }
        .platform-checkbox { display: inline-block; margin: 10px; }
    </style>
</head>
<body>
    <h1>Content Generation System</h1>
    
    <h2>Create New Project</h2>
    <form method="POST" action="/create_project">
        <div class="form-group">
            <label>Project Name:</label>
            <input type="text" name="name" required>
        </div>
        
        <div class="form-group">
            <label>Description:</label>
            <textarea name="description" required></textarea>
        </div>
        
        <div class="form-group">
            <label>Brand Voice:</label>
            <select name="brand_voice">
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
                <option value="friendly">Friendly</option>
                <option value="authoritative">Authoritative</option>
                <option value="playful">Playful</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>Target Platforms:</label>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="twitter"> Twitter
            </div>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="linkedin"> LinkedIn
            </div>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="facebook"> Facebook
            </div>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="instagram"> Instagram
            </div>
        </div>
        
        <div class="form-group">
            <label>Industry:</label>
            <input type="text" name="industry" required>
        </div>
        
        <div class="form-group">
            <label>Target Audience:</label>
            <textarea name="target_audience" required></textarea>
        </div>
        
        <button type="submit">Create Project</button>
    </form>
    
    <h2>Existing Projects</h2>
    {% for project in projects %}
    <div class="project-card">
        <h3>{{ project.name }}</h3>
        <p>{{ project.description }}</p>
        <p><strong>Platforms:</strong> {{ ', '.join(project.platforms) }}</p>
        <a href="/generate_content/{{ project._id }}">Generate Content</a>
    </div>
    {% endfor %}
</body>
</html>
"""

CONTENT_GENERATION_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Generate Content - {{ project.name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .form-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, select { width: 100%; padding: 8px; margin-bottom: 10px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .content-preview { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Generate Content for {{ project.name }}</h1>
    
    <form method="POST" action="/generate_content/{{ project._id }}">
        <div class="form-group">
            <label>Content Topic:</label>
            <input type="text" name="topic" required>
        </div>
        
        <div class="form-group">
            <label>Target Platform:</label>
            <select name="target_platform" id="target_platform" onchange="updateContentTypes()">
                {% for platform in project.platforms %}
                <option value="{{ platform }}">{{ platform.title() }}</option>
                {% endfor %}
            </select>
        </div>
        
        <div class="form-group">
            <label>Content Type:</label>
            <select name="content_type" id="content_type">
                <!-- Options will be populated by JavaScript -->
            </select>
        </div>
        
        <div class="form-group">
            <label>Additional Context:</label>
            <textarea name="context" placeholder="Any specific requirements or context..."></textarea>
        </div>
        
        <button type="submit">Generate Content</button>
    </form>
    
    {% if generated_content %}
    <h2>Generated Content</h2>
    <div class="content-preview">
        <h3>{{ generated_content.platform.title() }} Content</h3>
        <p><strong>Type:</strong> {{ generated_content.content_type }}</p>
        <div style="background: #f8f9fa; padding: 15px; margin: 10px 0;">
            {{ generated_content.content | safe }}
        </div>
        
        {% if generated_content.hashtags %}
        <p><strong>Hashtags:</strong> {{ generated_content.hashtags | join(', ') }}</p>
        {% endif %}
        
        <form method="POST" action="/schedule_content">
            <input type="hidden" name="content_id" value="{{ generated_content._id }}">
            <div class="form-group">
                <label>Schedule for:</label>
                <input type="datetime-local" name="schedule_time" required>
            </div>
            <button type="submit">Schedule Post</button>
        </form>
        
        <form method="POST" action="/post_now" style="display: inline;">
            <input type="hidden" name="content_id" value="{{ generated_content._id }}">
            <button type="submit">Post Now</button>
        </form>
    </div>
    {% endif %}

    <script>
        // Platform-specific content types mapping
        const platformContentTypes = {
            'twitter': [
                { value: 'post', text: 'Tweet' },
                { value: 'thread', text: 'Twitter Thread' },
                { value: 'poll', text: 'Twitter Poll' }
            ],
            'linkedin': [
                { value: 'post', text: 'Professional Post' },
                { value: 'article', text: 'LinkedIn Article' },
                { value: 'carousel', text: 'Carousel Post' },
                { value: 'poll', text: 'LinkedIn Poll' }
            ],
            'facebook': [
                { value: 'post', text: 'Facebook Post' },
                { value: 'story', text: 'Facebook Story' },
                { value: 'poll', text: 'Facebook Poll' },
                { value: 'event', text: 'Event Post' }
            ],
            'instagram': [
                { value: 'post', text: 'Instagram Post' },
                { value: 'story', text: 'Instagram Story' },
                { value: 'reel', text: 'Instagram Reel' },
                { value: 'carousel', text: 'Carousel Post' }
            ]
        };

        function updateContentTypes() {
            const platformSelect = document.getElementById('target_platform');
            const contentTypeSelect = document.getElementById('content_type');
            const selectedPlatform = platformSelect.value;
            
            // Clear existing options
            contentTypeSelect.innerHTML = '';
            
            // Get content types for selected platform
            const contentTypes = platformContentTypes[selectedPlatform] || platformContentTypes['twitter'];
            
            // Add new options
            contentTypes.forEach(type => {
                const option = document.createElement('option');
                option.value = type.value;
                option.textContent = type.text;
                contentTypeSelect.appendChild(option);
            });
        }

        // Initialize content types on page load
        document.addEventListener('DOMContentLoaded', function() {
            updateContentTypes();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main dashboard showing all projects"""
    projects = mongodb_manager.get_all_projects()
    return render_template_string(PROJECT_FORM_HTML, projects=projects)

@app.route('/create_project', methods=['POST'])
async def create_project():
    """Create a new project"""
    try:
        project_data = {
            'name': request.form['name'],
            'description': request.form['description'],
            'brand_voice': request.form['brand_voice'],
            'platforms': request.form.getlist('platforms'),
            'industry': request.form['industry'],
            'target_audience': request.form['target_audience'],
            'created_at': datetime.utcnow(),
            'status': 'active'
        }
        
        project_id = mongodb_manager.create_project(project_data)
        
        # Create vector embeddings for project context
        await qdrant_manager.create_project_collection(project_id)
        
        return jsonify({'success': True, 'project_id': str(project_id)})
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_content/<project_id>')
def generate_content_form(project_id):
    """Show content generation form"""
    project = mongodb_manager.get_project(project_id)
    return render_template_string(CONTENT_GENERATION_HTML, project=project)

@app.route('/generate_content/<project_id>', methods=['POST'])
async def generate_content(project_id):
    """Generate content using CrewAI agents"""
    try:
        project = mongodb_manager.get_project(project_id)
        
        content_request = {
            'topic': request.form['topic'],
            'content_type': request.form['content_type'],
            'target_platform': request.form['target_platform'],
            'context': request.form.get('context', ''),
            'project': project
        }
        
        # Generate content using CrewAI
        generated_content = await crew_manager.generate_content(content_request)
        
        # Save generated content
        content_id = mongodb_manager.save_content(project_id, generated_content)
        generated_content['_id'] = content_id
        
        return render_template_string(
            CONTENT_GENERATION_HTML, 
            project=project, 
            generated_content=generated_content
        )
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/schedule_content', methods=['POST'])
def schedule_content():
    """Schedule content for posting"""
    try:
        content_id = request.form['content_id']
        schedule_time = datetime.fromisoformat(request.form['schedule_time'])
        
        # Add to scheduler
        scheduler_service.schedule_post(content_id, schedule_time)
        
        return jsonify({'success': True, 'message': 'Content scheduled successfully'})
    except Exception as e:
        logger.error(f"Error scheduling content: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/post_now', methods=['POST'])
async def post_now():
    """Post content immediately"""
    try:
        content_id = request.form['content_id']
        logger.info(f"Attempting to post content: {content_id}")
        
        # Get content from database
        content = mongodb_manager.get_content(content_id)
        if not content:
            logger.error(f"Content not found: {content_id}")
            return jsonify({'error': 'Content not found'}), 404
        
        logger.info(f"Found content for platform: {content.get('platform')}")
        
        # Validate content has required fields
        if not content.get('platform'):
            logger.error("Content missing platform information")
            return jsonify({'error': 'Content missing platform information'}), 400
            
        if not content.get('content'):
            logger.error("Content missing text content")
            return jsonify({'error': 'Content missing text content'}), 400
        
        # Post to social media
        logger.info(f"Posting to {content['platform']}")
        result = await social_media_service.post_content(content)
        
        if not result.get('success'):
            logger.error(f"Posting failed: {result}")
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown posting error'),
                'post_result': result
            }), 400
        
        # Test the posted content (if test function exists)
        test_result = None
        try:
            test_result = await crew_manager.test_content(content_id, result)
        except Exception as test_error:
            logger.warning(f"Content testing failed but posting succeeded: {test_error}")
            test_result = {'error': str(test_error)}
        
        # Update content status
        mongodb_manager.update_content_status(content_id, 'posted', result)
        logger.info(f"Content posted successfully: {content_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Content posted successfully',
            'post_result': result,
            'test_result': test_result
        })
        
    except Exception as e:
        logger.error(f"Error posting content: {e}")
        return jsonify({
            'success': False,
            'error': f'Posting failed: {str(e)}'
        }), 500

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """API endpoint to get all projects"""
    projects = mongodb_manager.get_all_projects()
    return jsonify([{
        '_id': str(p['_id']),
        'name': p['name'],
        'description': p['description'],
        'platforms': p['platforms'],
        'status': p['status']
    } for p in projects])

@app.route('/api/content/<project_id>', methods=['GET'])
def api_get_content(project_id):
    """API endpoint to get content for a project"""
    content = mongodb_manager.get_project_content(project_id)
    return jsonify([{
        '_id': str(c['_id']),
        'content': c['content'],
        'platform': c['platform'],
        'status': c['status'],
        'created_at': c['created_at'].isoformat()
    } for c in content])

@app.route('/test_facebook', methods=['GET'])
async def test_facebook():
    """Test Facebook API connection"""
    try:
        result = await social_media_service.test_facebook_connection()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing Facebook connection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Start the scheduler in a separate thread
    scheduler_service.start()
    
    # Start MCP server
    mcp_server.start()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
