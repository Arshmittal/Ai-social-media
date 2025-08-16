# AI-Powered Content Generation System

A sophisticated content generation and social media management platform that leverages **Model Context Protocol (MCP)** and **CrewAI** to create, schedule, and publish high-quality content across multiple social media platforms.

## 🚀 Overview

This system combines the power of AI agents, vector databases, and social media APIs to automate content creation and management. It uses **MCP (Model Context Protocol)** for standardized AI tool communication and **CrewAI** for orchestrating specialized AI agents that work together to research, create, and optimize content.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   MCP Server    │    │   CrewAI Agents │
│   (Flask App)   │◄──►│   (Tool Bridge) │◄──►│   (AI Workers)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MongoDB       │    │   Qdrant        │    │   Social Media  │
│   (Projects &   │    │   (Vector DB)   │    │   APIs          │
│    Content)     │    │   (Similarity)  │    │   (Publishing)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Key Technologies

- **MCP (Model Context Protocol)**: Enables standardized communication between AI tools and the system
- **CrewAI**: Orchestrates specialized AI agents for content creation workflows
- **Flask**: Web interface for project management and content generation
- **MongoDB**: Stores projects, content, and user data
- **Qdrant**: Vector database for content similarity search and recommendations
- **OpenAI/Mistral**: AI models for content generation
- **Social Media APIs**: Twitter, LinkedIn, Facebook, Instagram integration

## 🎯 What MCP (Model Context Protocol) Does

MCP serves as the **communication bridge** between different AI tools and our system. Here's why it's essential:

### 🔗 **Standardized Tool Communication**
- Provides a unified interface for AI tools to interact with the system
- Enables seamless integration of new AI capabilities without code changes
- Standardizes how tools request data and return results

### 🛠️ **Available MCP Tools**
- `get_project_info`: Retrieve project details and settings
- `generate_content`: Create platform-specific content
- `schedule_content`: Schedule posts for automatic publishing
- `get_analytics`: Fetch performance metrics for posted content
- `search_similar_content`: Find similar content using vector similarity

### 🔄 **Real-time Integration**
- Tools can access live project data and system state
- Enables dynamic content generation based on current trends
- Provides context-aware recommendations

## 🤖 How CrewAI Powers Content Creation

CrewAI orchestrates specialized AI agents that work together to create high-quality content:

### 👥 **Specialized Agents**
1. **Content Researcher**: Analyzes trends and finds relevant topics
2. **Content Creator**: Generates platform-specific content
3. **Content Optimizer**: Refines content for maximum engagement
4. **Media Specialist**: Suggests and creates visual content

### 🔄 **Collaborative Workflow**
```
Research Agent → Creator Agent → Optimizer Agent → Media Agent
     ↓              ↓              ↓              ↓
  Find Trends → Generate → Refine → Add Media → Final Content
```

### 🎨 **Platform-Specific Optimization**
Each agent understands platform requirements:
- **Twitter**: 280 characters, trending hashtags, thread support
- **LinkedIn**: Professional tone, industry insights, article format
- **Facebook**: Engaging content, community focus, story format
- **Instagram**: Visual-first, hashtag optimization, story/carousel support

## 📋 Features

### 🎯 **Project Management**
- Create and manage content projects
- Define brand voice and target audience
- Set platform-specific requirements
- Track project performance

### 🚀 **Content Generation**
- **AI-Powered Creation**: Generate content using advanced AI models
- **Platform Optimization**: Automatically adapt content for each platform
- **Media Integration**: Suggest and create visual content
- **Brand Consistency**: Maintain consistent voice across all content

### 📅 **Smart Scheduling**
- **Optimal Timing**: Schedule posts for maximum engagement
- **Cross-Platform Coordination**: Coordinate content across multiple platforms
- **Automated Publishing**: Hands-free content distribution
- **Schedule Management**: Edit and reschedule content easily

### 📊 **Analytics & Insights**
- **Performance Tracking**: Monitor engagement metrics
- **Content Analysis**: Identify top-performing content
- **Trend Insights**: Discover trending topics and hashtags
- **ROI Measurement**: Track content effectiveness

### 🔍 **Content Discovery**
- **Similarity Search**: Find similar content using vector search
- **Trend Research**: Discover trending topics in your industry
- **Competitor Analysis**: Analyze competitor content strategies
- **Content Recommendations**: Get AI-powered content suggestions

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- MongoDB
- Qdrant Vector Database
- Social Media API Keys

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd content-generation-system

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Initialize databases
python startup.py
```

### Environment Variables
```env
# AI Services
OPENAI_API_KEY=your_openai_key
MISTRAL_API_KEY=your_mistral_key

# Database
MONGODB_URI=your_mongodb_uri
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Social Media APIs
TWITTER_API_KEY=your_twitter_key
LINKEDIN_CLIENT_ID=your_linkedin_id
FACEBOOK_ACCESS_TOKEN=your_facebook_token
INSTAGRAM_ACCESS_TOKEN=your_instagram_token

# System Configuration
FLASK_SECRET_KEY=your_secret_key
MCP_HOST=localhost
MCP_PORT=8001
```

## 🚀 Usage

### Starting the System
```bash
# Start all services
python startup.py

# Or start individual components
python main.py  # Web interface
python -m mcp.mcp_server  # MCP server
```

### Web Interface
1. Open `http://localhost:5000` in your browser
2. Create a new project with your brand details
3. Generate content for specific platforms
4. Schedule and publish content automatically

### API Endpoints
- `POST /create_project`: Create a new content project
- `POST /generate_content/<project_id>`: Generate content for a project
- `GET /projects`: List all projects
- `POST /schedule_content`: Schedule content for publishing
- `GET /analytics/<project_id>`: Get project analytics

## 🔧 Configuration

### Platform Settings
Each platform has specific configurations:
- **Character limits** and **formatting requirements**
- **Hashtag strategies** and **engagement tactics**
- **Content type support** (posts, stories, articles, polls)
- **Optimal posting times** and **frequency**

### AI Model Configuration
- **OpenAI GPT-4**: High-quality content generation
- **Mistral**: Fast and cost-effective generation
- **Custom prompts**: Platform-specific optimization
- **Brand voice adaptation**: Consistent tone across content

## 📈 Performance & Scalability

### 🚀 **High Performance**
- **Async Processing**: Non-blocking content generation
- **Vector Search**: Fast similarity matching
- **Caching**: Optimized database queries
- **Background Tasks**: Scheduled content processing

### 📊 **Scalability Features**
- **Modular Architecture**: Easy to add new platforms
- **Microservices Ready**: Can be containerized and scaled
- **Database Optimization**: Efficient indexing and queries
- **Load Balancing**: Handle multiple concurrent requests

## 🔒 Security & Privacy

- **API Key Management**: Secure storage of social media credentials
- **Data Encryption**: Encrypted storage of sensitive information
- **Access Control**: User authentication and authorization
- **Audit Logging**: Track all system activities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` folder for detailed guides
- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join community discussions for help and ideas

## 🔮 Roadmap

- [ ] **Advanced Analytics**: Deep learning-based performance prediction
- [ ] **Multi-language Support**: Content generation in multiple languages
- [ ] **Video Content**: AI-powered video creation and editing
- [ ] **Advanced Scheduling**: ML-based optimal timing prediction
- [ ] **Team Collaboration**: Multi-user project management
- [ ] **API Marketplace**: Third-party tool integrations

---

**Built with ❤️ using MCP and CrewAI for intelligent content creation**