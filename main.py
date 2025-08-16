
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string, redirect, send_from_directory
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
from services.image_service import ImageService
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
scheduler_service = SchedulerService(mongodb_manager=mongodb_manager, social_media_service=social_media_service)
image_service = ImageService("static/images")
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
        <div style="margin-top: 15px;">
            <a href="/generate_content/{{ project._id }}" style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; margin-right: 10px;">Generate Content</a>
            <a href="/edit_project/{{ project._id }}" style="background: #28a745; color: white; padding: 8px 16px; text-decoration: none; margin-right: 10px;">Edit</a>
            <a href="/delete_project/{{ project._id }}" onclick="return confirm('Are you sure you want to delete this project?')" style="background: #dc3545; color: white; padding: 8px 16px; text-decoration: none;">Delete</a>
        </div>
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
        .platform-info { background: #e9ecef; padding: 10px; margin: 10px 0; border-radius: 5px; font-size: 0.9em; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .char-counter { font-size: 0.8em; color: #666; }
    </style>
</head>
<body>
    <h1>Generate Content for {{ project.name }}</h1>
    
    <form method="POST" action="/generate_content/{{ project._id }}" enctype="multipart/form-data">
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
            <select name="content_type" id="content_type" onchange="updatePlatformInfo()">
                <!-- Options will be populated by JavaScript -->
            </select>
        </div>
        
        <div id="platform-info" class="platform-info">
            <!-- Platform-specific info will be shown here -->
        </div>
        
        <div class="form-group">
            <div class="checkbox-group">
                <input type="checkbox" name="include_media" id="include_media" value="true">
                <label for="include_media" style="display: inline; margin: 0;">Include Media Suggestion</label>
            </div>
            <small class="char-counter">Adds image/video suggestions to your content</small>
        </div>
        
        <div class="form-group">
            <label>Upload Image (Optional):</label>
            <input type="file" name="media_file" accept="image/*,video/*" id="media_file">
            <small class="char-counter">Upload an image or video to include with your content</small>
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
        <h3>{{ generated_content.platform.title() }} {{ generated_content.content_type.title() }}</h3>
        <p><strong>Character Count:</strong> <span id="content-length">{{ generated_content.content|length }}</span></p>
        <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; white-space: pre-wrap;">{{ generated_content.content }}</div>
        
        {% if generated_content.hashtags %}
        <p><strong>Hashtags:</strong> {{ generated_content.hashtags | join(', ') }}</p>
        {% endif %}
        
        {% if generated_content.media_path %}
        <div style="margin: 15px 0;">
            <p><strong>Uploaded Media:</strong></p>
            <img src="/{{ generated_content.media_path }}" alt="Uploaded media" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd;">
        </div>
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
        
        <form method="POST" action="/regenerate_content" style="display: inline;">
            <input type="hidden" name="project_id" value="{{ project._id }}">
            <input type="hidden" name="topic" value="{{ request.form.get('topic', '') }}">
            <input type="hidden" name="content_type" value="{{ request.form.get('content_type', '') }}">
            <input type="hidden" name="target_platform" value="{{ request.form.get('target_platform', '') }}">
            <input type="hidden" name="context" value="{{ request.form.get('context', '') }}">
            <input type="hidden" name="include_media" value="{{ request.form.get('include_media', '') }}">
            {% if generated_content.media_path %}
            <input type="hidden" name="media_path" value="{{ generated_content.media_path }}">
            {% endif %}
            <button type="submit" style="background: #ffc107; color: #212529;">Regenerate Content</button>
        </form>
    </div>
    {% endif %}

    <script>
        // Enhanced platform-specific content types mapping with character limits
        const platformContentTypes = {
            'twitter': [
                { value: 'post', text: 'Tweet', maxLength: 280, description: 'Single tweet with concise message' },
                { value: 'thread', text: 'Twitter Thread', maxLength: 280, description: '3-5 connected tweets, each under 280 chars' },
                { value: 'poll', text: 'Twitter Poll', maxLength: 220, description: 'Poll question with 2-4 options' }
            ],
            'linkedin': [
                { value: 'post', text: 'Professional Post', maxLength: 3000, description: 'Professional update or insight' },
                { value: 'article', text: 'LinkedIn Article', maxLength: 8000, description: 'Long-form article content' },
                { value: 'poll', text: 'LinkedIn Poll', maxLength: 2800, description: 'Professional poll with context' }
            ],
            'facebook': [
                { value: 'post', text: 'Facebook Post', maxLength: 2000, description: 'Engaging personal/brand story' },
                { value: 'story', text: 'Facebook Story', maxLength: 500, description: 'Short, visual-focused content' },
                { value: 'poll', text: 'Facebook Poll', maxLength: 1800, description: 'Interactive poll with reactions' }
            ],
            'instagram': [
                { value: 'post', text: 'Instagram Post', maxLength: 2200, description: 'Visual-first caption' },
                { value: 'story', text: 'Instagram Story', maxLength: 200, description: 'Brief, engaging story text' },
                { value: 'reel', text: 'Instagram Reel', maxLength: 1000, description: 'Short video description' }
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
            
            // Update platform info
            updatePlatformInfo();
        }
        
        function updatePlatformInfo() {
            const platformSelect = document.getElementById('target_platform');
            const contentTypeSelect = document.getElementById('content_type');
            const platformInfoDiv = document.getElementById('platform-info');
            
            const selectedPlatform = platformSelect.value;
            const selectedContentType = contentTypeSelect.value;
            
            const contentTypes = platformContentTypes[selectedPlatform] || platformContentTypes['twitter'];
            const contentTypeInfo = contentTypes.find(type => type.value === selectedContentType);
            
            if (contentTypeInfo) {
                platformInfoDiv.innerHTML = `
                    <strong>${selectedPlatform.charAt(0).toUpperCase() + selectedPlatform.slice(1)} ${contentTypeInfo.text}</strong><br>
                    📝 ${contentTypeInfo.description}<br>
                    📊 Character Limit: ${contentTypeInfo.maxLength} characters
                `;
            }
        }

        // Initialize content types on page load
        document.addEventListener('DOMContentLoaded', function() {
            updateContentTypes();
        });
    </script>
</body>
</html>
"""

EDIT_PROJECT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit Project</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .form-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, select { width: 100%; padding: 8px; margin-bottom: 10px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; margin-right: 10px; }
        .cancel-btn { background: #6c757d; }
        .platform-checkbox { display: inline-block; margin: 10px; }
    </style>
</head>
<body>
    <h1>Edit Project</h1>
    
    <form method="POST" action="/edit_project/{{ project._id }}">
        <div class="form-group">
            <label>Project Name:</label>
            <input type="text" name="name" value="{{ project.name }}" required>
        </div>
        
        <div class="form-group">
            <label>Description:</label>
            <textarea name="description" required>{{ project.description }}</textarea>
        </div>
        
        <div class="form-group">
            <label>Brand Voice:</label>
            <select name="brand_voice">
                <option value="professional" {% if project.brand_voice == 'professional' %}selected{% endif %}>Professional</option>
                <option value="casual" {% if project.brand_voice == 'casual' %}selected{% endif %}>Casual</option>
                <option value="friendly" {% if project.brand_voice == 'friendly' %}selected{% endif %}>Friendly</option>
                <option value="authoritative" {% if project.brand_voice == 'authoritative' %}selected{% endif %}>Authoritative</option>
                <option value="playful" {% if project.brand_voice == 'playful' %}selected{% endif %}>Playful</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>Target Platforms:</label>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="twitter" {% if 'twitter' in project.platforms %}checked{% endif %}> Twitter
            </div>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="linkedin" {% if 'linkedin' in project.platforms %}checked{% endif %}> LinkedIn
            </div>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="facebook" {% if 'facebook' in project.platforms %}checked{% endif %}> Facebook
            </div>
            <div class="platform-checkbox">
                <input type="checkbox" name="platforms" value="instagram" {% if 'instagram' in project.platforms %}checked{% endif %}> Instagram
            </div>
        </div>
        
        <div class="form-group">
            <label>Industry:</label>
            <input type="text" name="industry" value="{{ project.industry }}" required>
        </div>
        
        <div class="form-group">
            <label>Target Audience:</label>
            <textarea name="target_audience" required>{{ project.target_audience }}</textarea>
        </div>
        
        <button type="submit">Update Project</button>
        <a href="/" class="cancel-btn" style="color: white; text-decoration: none; padding: 10px 20px; display: inline-block;">Cancel</a>
    </form>
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

@app.route('/edit_project/<project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    """Edit project route"""
    if request.method == 'GET':
        project = mongodb_manager.get_project(project_id)
        if not project:
            return "Project not found", 404
        return render_template_string(EDIT_PROJECT_HTML, project=project)
    
    elif request.method == 'POST':
        try:
            platforms = request.form.getlist('platforms')
            if not platforms:
                return "At least one platform must be selected", 400
            
            updates = {
                'name': request.form['name'],
                'description': request.form['description'],
                'brand_voice': request.form['brand_voice'],
                'platforms': platforms,
                'industry': request.form['industry'],
                'target_audience': request.form['target_audience']
            }
            
            # Update project
            success = mongodb_manager.update_project(project_id, updates)
            
            if success:
                logger.info(f"Project updated: {project_id}")
                return redirect('/')
            else:
                return "Failed to update project", 500
                
        except Exception as e:
            logger.error(f"Error updating project: {e}")
            return f"Error: {str(e)}", 500

@app.route('/delete_project/<project_id>', methods=['GET'])
def delete_project(project_id):
    """Delete project route"""
    try:
        # Update project status to inactive instead of deleting
        success = mongodb_manager.update_project(project_id, {'status': 'deleted'})
        
        if success:
            logger.info(f"Project deleted: {project_id}")
            return redirect('/')
        else:
            return "Failed to delete project", 500
            
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return f"Error: {str(e)}", 500

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
        
        # Handle file upload
        media_path = None
        if 'media_file' in request.files and request.files['media_file'].filename:
            media_file = request.files['media_file']
            if media_file.filename:
                try:
                    media_path = image_service.save_uploaded_image(
                        media_file.read(), 
                        media_file.filename
                    )
                    logger.info(f"Media uploaded: {media_path}")
                except Exception as e:
                    logger.error(f"Error uploading media: {e}")
        
        content_request = {
            'topic': request.form['topic'],
            'content_type': request.form['content_type'],
            'target_platform': request.form['target_platform'],
            'context': request.form.get('context', ''),
            'include_media': request.form.get('include_media') == 'true',
            'media_path': media_path,
            'project': project
        }
        
        # Generate content using CrewAI
        generated_content = await crew_manager.generate_content(content_request)
        
        # Add media path to content data
        if media_path:
            generated_content['media_path'] = media_path
        
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

@app.route('/regenerate_content', methods=['POST'])
async def regenerate_content():
    """Regenerate content with the same parameters"""
    try:
        project_id = request.form['project_id']
        project = mongodb_manager.get_project(project_id)
        
        # Use the same parameters as the original request
        content_request = {
            'topic': request.form.get('topic', ''),
            'content_type': request.form.get('content_type', ''),
            'target_platform': request.form.get('target_platform', ''),
            'context': request.form.get('context', ''),
            'include_media': request.form.get('include_media', '') == 'true',
            'media_path': request.form.get('media_path', ''),
            'project': project
        }
        
        # Generate new content
        content_data = await crew_manager.generate_content(content_request)
        
        # Add media path to content data if it exists
        if content_request.get('media_path'):
            content_data['media_path'] = content_request['media_path']
        
        # Save the new content
        content_id = mongodb_manager.save_content(project_id, content_data)
        content_data['_id'] = content_id
        
        # Render the form again with new content
        return render_template_string(CONTENT_GENERATION_HTML, 
                                    project=project, 
                                    generated_content=content_data,
                                    request=request)
        
    except Exception as e:
        logger.error(f"Error regenerating content: {e}")
        return f"Error regenerating content: {str(e)}", 500

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

@app.route('/static/images/<filename>')
def serve_image(filename):
    """Serve uploaded images"""
    return send_from_directory('static/images', filename)

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

if __name__ == '__main__':
    # Start the scheduler in a separate thread
    scheduler_service.start()
    
    # Start MCP server
    mcp_server.start()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
