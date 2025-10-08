# GPT-4 Token Usage Analysis for OpenRouter Integration

## 🔍 **Current Token Usage Tracking**

### **Configuration Settings**
- **Model**: GPT-4o via OpenRouter
- **Max Tokens**: 4,000 per request (for comprehensive VRL generation)
- **Temperature**: 0.1 (for consistent parsing)
- **Base URL**: https://openrouter.ai/api/v1

### **Estimated Token Usage Per Request**

#### **1. Log Classification Request**
- **Input Tokens**: ~800-1,200 tokens
  - System prompt: ~300 tokens
  - Log content: ~100-500 tokens
  - RAG context: ~400-700 tokens
- **Output Tokens**: ~200-400 tokens
- **Total**: ~1,000-1,600 tokens per classification

#### **2. VRL Generation Request**
- **Input Tokens**: ~1,500-2,500 tokens
  - System prompt: ~500 tokens
  - Log content: ~100-500 tokens
  - RAG context: ~800-1,200 tokens
  - VRL requirements: ~200 tokens
- **Output Tokens**: ~1,000-2,000 tokens (comprehensive VRL code)
- **Total**: ~2,500-4,500 tokens per VRL generation

#### **3. ECS JSON Generation Request**
- **Input Tokens**: ~600-1,000 tokens
- **Output Tokens**: ~300-600 tokens
- **Total**: ~900-1,600 tokens per ECS generation

### **Cost Analysis (GPT-4o Pricing)**
- **Input**: $0.0025 per 1K tokens
- **Output**: $0.01 per 1K tokens

#### **Per Request Costs**:
- **Log Classification**: $0.003-$0.010
- **VRL Generation**: $0.008-$0.025
- **ECS Generation**: $0.003-$0.010

#### **Typical Workflow Cost**:
- **Complete parsing** (classification + VRL + ECS): ~$0.014-$0.045 per log
- **VRL-only generation**: ~$0.008-$0.025 per log

### **Usage Patterns Observed**

#### **From Terminal Logs**:
```
INFO:httpx:HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
```
- Multiple successful requests observed
- All returning 200 OK status
- No 402 Payment Required errors with new API key

#### **Request Frequency**:
- **UI Loading**: 8-10 requests (RAG initialization + agent setup)
- **Per Log Parse**: 3-4 requests (classification, VRL generation, ECS mapping)
- **Per UI Interaction**: 1-2 additional requests

### **Daily Usage Estimates**

#### **Light Usage** (10 logs/day):
- **Requests**: ~30-50 requests
- **Tokens**: ~75,000-150,000 tokens
- **Cost**: ~$1.00-$2.50/day

#### **Medium Usage** (100 logs/day):
- **Requests**: ~300-500 requests
- **Tokens**: ~750,000-1,500,000 tokens
- **Cost**: ~$10.00-$25.00/day

#### **Heavy Usage** (1000 logs/day):
- **Requests**: ~3,000-5,000 requests
- **Tokens**: ~7,500,000-15,000,000 tokens
- **Cost**: ~$100.00-$250.00/day

### **Token Optimization Strategies**

#### **1. Prompt Optimization**:
- Reduce RAG context size (currently ~1,000 tokens)
- Use more concise system prompts
- Implement prompt caching

#### **2. Response Optimization**:
- Limit VRL output length (currently ~2,000 tokens)
- Use templates for common patterns
- Implement response compression

#### **3. Caching Strategies**:
- Cache similar log patterns
- Reuse VRL templates
- Implement result memoization

### **Monitoring Recommendations**

#### **1. Real-time Tracking**:
```python
# Token tracking integrated into enhanced_openrouter_agent.py
track_openrouter_usage(response.response_metadata['token_usage'], "gpt-4o")
```

#### **2. Cost Alerts**:
- Set daily/monthly spending limits
- Monitor token usage trends
- Alert on unusual usage patterns

#### **3. Usage Reports**:
- Daily token consumption reports
- Cost per log analysis
- Performance vs cost optimization

### **Current Status**
- ✅ **API Key**: Working (new key active)
- ✅ **Token Tracking**: Implemented but needs testing
- ✅ **Cost Monitoring**: Available via token_usage_tracker.py
- ✅ **Usage Optimization**: Configurable max_tokens setting

### **Next Steps**
1. **Enable Token Tracking**: Test with actual UI usage
2. **Monitor Costs**: Run token_usage_tracker.py regularly
3. **Optimize Usage**: Adjust max_tokens based on needs
4. **Set Limits**: Configure spending alerts in OpenRouter dashboard

