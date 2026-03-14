# MLX-LM Optimization Code Examples

## Example 1: Basic Optimized Single-Request Inference

```python
from mlx_lm import stream_generate, load

# Load model with lazy loading for faster startup
model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit", lazy=True)

# Generate with optimized parameters
prompt = "Explain quantum computing in simple terms."

for response in stream_generate(
    model,
    tokenizer,
    prompt,
    max_tokens=256,
    temp=0.7,
    top_p=0.95,
    # Already using async_eval and Metal streams by default
):
    print(response.text, end="", flush=True)

print(f"\nPeak memory: {response.peak_memory:.2f} GB")
print(f"Generation speed: {response.generation_tps:.2f} tok/s")
```

---

## Example 2: Batch Generation for Maximum Throughput

```python
from mlx_lm import batch_generate, load

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

prompts = [
    "What is machine learning?",
    "Explain neural networks",
    "What are transformers?",
    "How does attention work?",
    "What is CUDA?",
]

# Convert to token lists (required format for batch_generate)
prompt_tokens = [tokenizer.encode(p) for p in prompts]

# Batch generation with continuous batching
responses = batch_generate(
    model,
    tokenizer,
    prompt_tokens,
    max_tokens=128,
    completion_batch_size=32,  # Concurrent tokens in flight
    prefill_batch_size=4,       # Prefill parallelism
    verbose=True
)

for i, (prompt, response) in enumerate(zip(prompts, responses.texts)):
    print(f"\n--- Query {i+1} ---")
    print(f"Q: {prompt}")
    print(f"A: {response}")

print(f"\nStats:")
print(f"  Prompt tokens: {responses.stats.prompt_tokens} @ {responses.stats.prompt_tps:.2f} tok/s")
print(f"  Generation tokens: {responses.stats.generation_tokens} @ {responses.stats.generation_tps:.2f} tok/s")
print(f"  Peak memory: {responses.stats.peak_memory:.2f} GB")
```

---

## Example 3: Prompt Caching for System Prompts

```python
from mlx_lm import stream_generate, load
from mlx_lm.models.cache import make_prompt_cache, save_prompt_cache, load_prompt_cache

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

# === Phase 1: Create and cache system prompt (one-time) ===
system_prompt = """You are a helpful AI assistant. 
- Be concise and clear.
- Provide accurate information.
- Ask clarifying questions if needed.
"""

# Create cache for system prompt
system_cache = make_prompt_cache(model)

# Pre-process the system prompt
system_tokens = tokenizer.encode(system_prompt)
prompt_array = make_prompt_cache(model)

# Save cache to file for reuse
save_prompt_cache("system_prompt_cache.safetensors", system_cache, 
                  {"model": "Llama-3.2-3B", "system_prompt": system_prompt})

# === Phase 2: Use cached system prompt for multiple queries ===
# Load cached system prompt
cached_system, metadata = load_prompt_cache("system_prompt_cache.safetensors", 
                                           return_metadata=True)

# Multiple user queries
queries = [
    "What is recursion?",
    "Explain sorting algorithms",
    "How do databases work?",
]

for query in queries:
    # Combine system prompt (cached) + user query
    combined_input = system_prompt + "\n\nUser: " + query
    combined_tokens = tokenizer.encode(combined_input)
    
    print(f"\nQuery: {query}")
    print("Answer: ", end="", flush=True)
    
    # Use cached system prompt - saves reprocessing!
    for response in stream_generate(
        model,
        tokenizer,
        combined_tokens,
        prompt_cache=cached_system.copy(),  # Copy to avoid mutation
        max_tokens=256,
    ):
        print(response.text, end="", flush=True)
    
    print(f" (Speed: {response.generation_tps:.2f} tok/s)")
```

---

## Example 4: KV Cache Quantization for Long Sequences

```python
from mlx_lm import stream_generate, load

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

# Long context document
long_document = """
[Your 10K+ token document here]
...
"""

long_prompt = f"Summarize the key points from this document:\n\n{long_document}"

print("Generating with KV cache quantization (4-bit)...")
print(f"Prompt tokens: {len(tokenizer.encode(long_prompt))}")

for response in stream_generate(
    model,
    tokenizer,
    long_prompt,
    max_tokens=256,
    # KV Cache Quantization Settings
    kv_bits=4,                  # 4-bit quantization (25% size)
    kv_group_size=64,           # Quantization group size
    quantized_kv_start=5000,    # Start quantizing after 5000 tokens
):
    print(response.text, end="", flush=True)

print(f"\nMemory used: {response.peak_memory:.2f} GB")
print(f"Speed: {response.generation_tps:.2f} tok/s")

# Estimate memory savings:
# Standard float16 KV cache: 2 bytes per value
# 4-bit quantized: 0.5 bytes per value (75% savings)
# For 10K token context: saves ~200MB per layer
```

---

## Example 5: Advanced Batch Generation with Per-Request Customization

```python
from mlx_lm import batch_generate, load
from mlx_lm.sample_utils import make_sampler

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

# Different prompts with different temperature requirements
queries = [
    "Generate a creative story about space exploration",  # High temp
    "What is the capital of France?",                      # Low temp
    "Explain a complex topic in simple terms",            # Medium temp
]

# Create different samplers for different purposes
creative_sampler = make_sampler(temp=0.9, top_p=0.95)   # Creative
factual_sampler = make_sampler(temp=0.0, top_p=1.0)     # Deterministic
neutral_sampler = make_sampler(temp=0.7, top_p=0.9)     # Balanced

# Use per-request samplers
token_lists = [tokenizer.encode(q) for q in queries]
samplers = [creative_sampler, factual_sampler, neutral_sampler]

responses = batch_generate(
    model,
    tokenizer,
    token_lists,
    samplers=samplers,           # Different sampler per request
    completion_batch_size=32,
    prefill_batch_size=8,
    verbose=True
)

for query, response in zip(queries, responses.texts):
    print(f"\nQ: {query}")
    print(f"A: {response[:200]}...")  # First 200 chars
```

---

## Example 6: Rotating KV Cache for Continuous Streaming

```python
from mlx_lm import stream_generate, load
from mlx_lm.models.cache import RotatingKVCache, make_prompt_cache

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

# RotatingKVCache keeps only recent tokens (circular buffer)
# This prevents unbounded memory growth for very long sequences

def stream_with_bounded_memory(prompt, max_context=4096):
    """Stream generation with bounded KV cache size."""
    
    # Create rotating cache with max 4K tokens
    rotating_cache = []
    for layer in model.layers:
        cache = RotatingKVCache(max_size=max_context, keep=4)
        rotating_cache.append(cache)
    
    for response in stream_generate(
        model,
        tokenizer,
        prompt,
        prompt_cache=rotating_cache,
        max_tokens=1024,
    ):
        yield response

# Use it
prompt = "Write a 2000-token essay about AI. " * 10  # Very long
tokens = 0

for response in stream_with_bounded_memory(prompt, max_context=4096):
    tokens += 1
    if tokens % 100 == 0:
        print(f"Generated {tokens} tokens, memory: {response.peak_memory:.2f} GB")
    if tokens % 50 == 0:
        print(response.text, end="", flush=True)
```

---

## Example 7: Pre-Loading and Warming Up GPU

```python
from mlx_lm import load, stream_generate
import mlx.core as mx

# Pre-load model to eliminate warmup latency
print("Loading model...")
model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit", lazy=False)

# Warmup: generate a token to warm up Metal compiler
print("Warming up GPU...")
_ = list(stream_generate(
    model,
    tokenizer,
    "Hi",  # Minimal warmup
    max_tokens=1
))

# Now measure actual inference speed
print("\nMeasuring inference speed...")
test_prompts = [
    "Explain recursion in 50 words",
    "What is a hash table?",
    "Describe machine learning",
]

for prompt in test_prompts:
    responses = []
    for response in stream_generate(
        model,
        tokenizer,
        prompt,
        max_tokens=100,
    ):
        responses.append(response)
    
    final_response = responses[-1]
    print(f"\n{prompt}")
    print(f"  Speed: {final_response.generation_tps:.2f} tok/s")
    print(f"  Memory: {final_response.peak_memory:.2f} GB")
```

---

## Example 8: Metal Configuration and Stream Management

```python
from mlx_lm import stream_generate, load
import mlx.core as mx

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

# Check Metal availability
if mx.metal.is_available():
    print("✅ Metal acceleration available")
    device_info = mx.device_info()
    print(f"   Max working set: {device_info['max_recommended_working_set_size'] / 1e9:.1f} GB")
    print(f"   Memory: {device_info['memory'] / 1e9:.1f} GB")
else:
    print("⚠️ Metal not available, using CPU (slow)")

# The wired_limit is automatically managed in stream_generate,
# but you can also control it manually:

print("\nGenerating with manual stream management...")

for response in stream_generate(
    model,
    tokenizer,
    "Explain neural networks in detail. " * 5,
    max_tokens=512,
    # Stream management is automatic via:
    # - generation_stream (dedicated Metal stream)
    # - mx.async_eval() (async command batching)
    # - wired_limit() (automatic memory limit)
):
    print(response.text, end="", flush=True)

print(f"\nFinal memory: {response.peak_memory:.2f} GB")
```

---

## Example 9: Comparing Optimization Strategies

```python
from mlx_lm import stream_generate, load
import time

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

prompt = "Write a detailed explanation of how transformers work in machine learning. " * 2
max_tokens = 256

# Strategy 1: Basic (no special optimizations)
print("Strategy 1: Basic generation")
tic = time.time()
for _ in stream_generate(model, tokenizer, prompt, max_tokens=max_tokens):
    pass
basic_time = time.time() - tic

# Strategy 2: With KV quantization
print("Strategy 2: With 4-bit KV quantization")
tic = time.time()
for _ in stream_generate(model, tokenizer, prompt, max_tokens=max_tokens,
                         kv_bits=4, kv_group_size=64):
    pass
quant_time = time.time() - tic

# Strategy 3: With prompt cache (pre-compute once)
from mlx_lm.models.cache import make_prompt_cache
print("Strategy 3: With prompt cache")
cache = make_prompt_cache(model)
tic = time.time()
for _ in stream_generate(model, tokenizer, prompt, max_tokens=max_tokens,
                         prompt_cache=cache):
    pass
cache_time = time.time() - tic

print(f"\nResults:")
print(f"  Basic: {basic_time:.2f}s (1.0x baseline)")
print(f"  4-bit KV: {quant_time:.2f}s ({basic_time/quant_time:.2f}x)")
print(f"  Cached: {cache_time:.2f}s ({basic_time/cache_time:.2f}x)")
```

---

## Example 10: Production Server with Optimizations

```python
from mlx_lm import load, stream_generate, batch_generate
from mlx_lm.models.cache import make_prompt_cache, save_prompt_cache, load_prompt_cache
import mlx.core as mx

class OptimizedLLMServer:
    def __init__(self, model_path="mlx-community/Llama-3.2-3B-Instruct-4bit"):
        # Load model once with lazy loading
        print("Loading model...")
        self.model, self.tokenizer = load(model_path, lazy=True)
        
        # Pre-compute system prompt cache
        self.system_prompt = """You are a helpful assistant."""
        self._init_system_cache()
        
    def _init_system_cache(self):
        """Pre-compute system prompt cache."""
        cache = make_prompt_cache(self.model)
        # Pre-process system prompt (in real usage, do this separately)
        save_prompt_cache("system_cache.safetensors", cache, 
                         {"system_prompt": self.system_prompt})
        self.system_cache, _ = load_prompt_cache("system_cache.safetensors", 
                                                 return_metadata=True)
    
    def generate_single(self, user_query, max_tokens=256):
        """Optimized single-request generation."""
        combined = self.system_prompt + "\nUser: " + user_query + "\nAssistant:"
        
        response_text = ""
        for response in stream_generate(
            self.model,
            self.tokenizer,
            combined,
            prompt_cache=self.system_cache.copy(),
            max_tokens=max_tokens,
            temp=0.7,
            top_p=0.95,
        ):
            response_text += response.text
        
        return {
            "text": response_text,
            "speed": response.generation_tps,
            "memory": response.peak_memory,
        }
    
    def generate_batch(self, queries, max_tokens=256):
        """Optimized batch generation for throughput."""
        query_tokens = [self.tokenizer.encode(q) for q in queries]
        
        responses = batch_generate(
            self.model,
            self.tokenizer,
            query_tokens,
            max_tokens=max_tokens,
            completion_batch_size=32,
            prefill_batch_size=8,
        )
        
        return {
            "responses": responses.texts,
            "generation_speed": responses.stats.generation_tps,
            "peak_memory": responses.stats.peak_memory,
        }

# Usage
if __name__ == "__main__":
    server = OptimizedLLMServer()
    
    # Single request (low latency)
    result = server.generate_single("What is AI?")
    print(f"Response: {result['text']}")
    print(f"Speed: {result['speed']:.2f} tok/s")
    
    # Batch requests (high throughput)
    results = server.generate_batch([
        "Explain ML",
        "What is NLP?",
        "How do neural networks work?",
    ])
    print(f"\nBatch generation speed: {results['generation_speed']:.2f} tok/s")
```

---

## Key Takeaways

1. **Always use `stream_generate()`** - It handles async_eval, Metal streams, and wired limits automatically
2. **For batch requests, use `batch_generate()`** - Much higher throughput (3-4x)
3. **Cache system prompts** - Pre-compute once, reuse across requests
4. **Enable KV quantization for long sequences** - 75% memory savings with minimal slowdown
5. **Use lazy loading in servers** - Faster startup, slightly slower first token
6. **Monitor response metrics** - `generation_tps` and `peak_memory` tell you if optimizations are working

