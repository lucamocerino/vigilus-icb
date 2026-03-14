# MLX-LM Optimization Opportunities for Inference Speed

## 1. PYTHON-LEVEL OVERHEAD IN TOKEN GENERATION LOOP

### Current Implementation (generate.py, lines 303-467)
The `generate_step()` function is the core token generation loop. Key characteristics:

**Current Flow:**
- Uses `mx.stream(generation_stream)` to isolate generation on a dedicated Metal stream
- Employs `mx.async_eval()` for asynchronous evaluation (lines 451, 456)
- Performs periodic cache management with `mx.clear_cache()` every 256 tokens (line 464)
- Uses synchronous `mx.eval()` at key synchronization points (line 458)

**Python-Level Overhead Identified:**
- Lines 405-412: Per-token logits processor loop with conditional concatenation
- Lines 414, 437-438: Quantization callback executed every token generation
- Lines 426-446: Prompt prefill loop with periodic synchronization and cache clearing
- Cache quantization (lines 295-300) happens in-place during generation

**Optimization Opportunity:**
The sampling loop (lines 453-466) has manageable overhead, but the quantization callbacks on every step could be optimized by batching quantization operations.

**Default State:** Async evaluation is enabled by default via `mx.async_eval()`

---

## 2. CONTINUOUS BATCHING & PROMPT CACHING SUPPORT

### ✅ **CONTINUOUS BATCHING - FULLY SUPPORTED**

**Implementation:** `BatchGenerator` class (lines 930-1322)

**Key Features:**
- **Batch Processing**: `batch_generate()` (line 1327) accepts multiple prompts
- **Completion Batch Size**: Configurable via `completion_batch_size` parameter (default 32)
- **Prefill Batch Size**: Configurable via `prefill_batch_size` parameter (default 8)
- **Dynamic Batching**: Prompts are sorted by length (line 1026-1029) for efficiency
- **KV Cache Management**: Supports `BatchKVCache` and `BatchRotatingKVCache` classes
- **Left-Padding**: Prompts are left-padded for batch processing (line 1094)
- **Watermarking**: Requests can be added and removed dynamically via `insert()` and `remove()`

**How to Use:**
```python
from mlx_lm import batch_generate, load

model, tokenizer = load(model_path)
prompts = [["A conversation about AI"], ["How to write code"]]
responses = batch_generate(
    model,
    tokenizer,
    prompts,
    max_tokens=256,
    completion_batch_size=32,  # Tokens in flight
    prefill_batch_size=8,       # Prefill batch size
    verbose=True
)
```

**Default State:** Not enabled by default - must explicitly use `batch_generate()`

---

### ✅ **PROMPT CACHING - FULLY SUPPORTED**

**Implementation:**
- `cache.make_prompt_cache()` (lines 13-38 in models/cache.py)
- `cache.save_prompt_cache()` and `cache.load_prompt_cache()` (lines 41-83)
- Integrated into `generate_step()` via `prompt_cache` parameter (line 311)

**Cache Types Available:**
- `KVCache`: Standard growing cache
- `RotatingKVCache`: Circular buffer with configurable max size
- `QuantizedKVCache`: Memory-optimized quantized keys/values
- `BatchKVCache`: For continuous batching with left-padded inputs
- `BatchRotatingKVCache`: Rotating cache for batched generation

**Features:**
- Pre-computed prompt caches can be saved and reused (cache_prompt.py)
- Caches preserve context while keeping memory bounded
- Supports trimming via `trim_prompt_cache()` (lines 93-109)

**How to Use:**
```python
from mlx_lm import stream_generate, load
from mlx_lm.models.cache import make_prompt_cache

model, tokenizer = load(model_path)
cache = make_prompt_cache(model, max_kv_size=4096)

# Use pre-computed cache in generation
for response in stream_generate(
    model,
    tokenizer,
    prompt,
    prompt_cache=cache,  # Reuse cache
):
    print(response.text, end="", flush=True)
```

**CLI Tool:**
```bash
python -m mlx_lm cache_prompt \
    --model model_path \
    --prompt "Your system prompt" \
    --prompt-cache-file system_cache.safetensors
```

**Default State:** Optional - no caching unless explicitly provided

---

## 3. CONFIGURATION OPTIONS & ENVIRONMENT VARIABLES

### Configuration Options in generate_step()
- `prefill_step_size` (int, default 2048): Chunk size for prompt processing
- `max_kv_size` (int, optional): Maximum KV cache size (rotating cache only)
- `kv_bits` (int, optional): Quantize KV cache to 4, 8, etc. bits
- `kv_group_size` (int, default 64): Group size for KV cache quantization
- `quantized_kv_start` (int, default 0): Token offset before starting KV quantization

### Model Loading Configuration
**File:** `utils.py`, `load_model()` function (lines 270-406)

```python
from mlx_lm import load

model, tokenizer = load(
    model_path,
    lazy=False,  # Eager evaluation (False = eval weights immediately)
    model_config={"quantize_activations": True},  # Quantize activations
)
```

### Environment Variables
- `MLXLM_USE_MODELSCOPE` (line 27 in utils.py): Set to "true" to use ModelScope instead of Hugging Face Hub
  ```bash
  export MLXLM_USE_MODELSCOPE=true
  ```

### BatchGenerator Configuration
```python
batch_gen = BatchGenerator(
    model,
    completion_batch_size=32,     # Tokens in flight
    prefill_batch_size=8,          # Prefill parallelism
    prefill_step_size=2048,        # Prefill chunk size
    max_kv_size=None,              # Max KV size for rotating cache
)
```

**Default State:** Eager loading (lazy=False), no activation quantization

---

## 4. MODEL LOADING - LAZY LOADING & MEMORY MAPPING

### Lazy Loading Support ✅

**Implementation:** `load()` function (lines 441-487 in utils.py)

```python
from mlx_lm import load

# Eager loading (DEFAULT - weights loaded immediately)
model, tokenizer = load(model_path, lazy=False)

# Lazy loading (weights loaded on first use)
model, tokenizer = load(model_path, lazy=True)
```

**What it does:**
- `lazy=True`: Weights remain on disk until first access (saves initial startup time)
- `lazy=False`: Weights are evaluated immediately into GPU memory
- Line 405: When lazy=False, `mx.eval(model.parameters())` forces GPU evaluation

**Timing Impact:**
- Lazy loading faster for large models at startup
- First token latency may increase slightly (weights being loaded)
- Subsequent tokens benefit from weights already in GPU

**Default State:** `lazy=False` (eager loading)

**Use Case:**
```python
# For serving scenarios with immediate inference:
model, tokenizer = load(model_path, lazy=True)  # Fast startup
# First prompt causes weight loading, then fast tokens
```

---

## 5. QUANTIZATION-AWARE OPTIMIZATIONS

### KV Cache Quantization ✅

**Implementation:** `QuantizedKVCache` class (lines 230-321 in models/cache.py)

**Features:**
- Line 275-276: On-the-fly quantization of keys/values during generation
- Dynamic allocation with 256-token chunks (line 231)
- Group-wise quantization with configurable group size and bit width

**How to Use:**
```python
from mlx_lm import stream_generate

for response in stream_generate(
    model,
    tokenizer,
    prompt,
    kv_bits=4,              # 4-bit quantization
    kv_group_size=64,       # Group size
    quantized_kv_start=5000 # Start quantizing after 5000 tokens
):
    pass
```

**Memory Savings:** 4-bit reduces KV cache to 25% of original size

**Default State:** No quantization unless specified

---

### Activation Quantization ✅

**Implementation:** Via model_config in load()

```python
model, tokenizer = load(
    model_path,
    model_config={"quantize_activations": True}
)
```

**Default State:** Disabled by default

---

### Fused Operations ✅

**Implementation:** Model-level fusion via `fuse()` method

```bash
# Fuse adapter weights into model
python -m mlx_lm fuse \
    --model model_path \
    --adapter-path adapter_path \
    --save-path fused_model
```

**What it does:** Merges linear layers with quantization scales for single-step computation

**Default State:** Not fused unless explicitly called

---

### Compiled Sampling ✅

**Implementation:** `sample_utils.py` (lines 111-276)

All sampling functions use `@mx.compile` decorator:
- `apply_top_k()` (line 111)
- `apply_min_p()` (line 136)
- `apply_top_p()` (line 201)
- `apply_xtc()` (line 237)
- `categorical_sampling()` (line 274)

These are pre-compiled Metal kernels for fast sampling on GPU.

**Default State:** Compiled and optimized by default

---

## 6. METAL COMMAND BUFFER BATCHING & SYNCHRONIZATION CONTROL

### Metal Stream Management ✅

**Implementation:** `generate.py` lines 220-262

**Key Components:**

```python
# Dedicated generation stream
generation_stream = mx.new_stream(mx.default_device())
```

**Usage in generation:**
```python
with mx.stream(generation_stream):
    logits = model(input_tokens)
    # All operations in this block use generation_stream
```

**Default State:** Used automatically in `stream_generate()` and `generate_step()`

---

### Async Evaluation (Metal Command Buffer Pipelining) ✅

**Implementation:** Lines 451, 456, 1172, 1248

```python
# Asynchronously queue next forward pass while Python processes current token
mx.async_eval(next_y, next_logprobs)
# Python code runs here (sampling, logit processing)
# Then synchronization happens when accessing next_y
```

**What it does:**
- Queues Metal commands without CPU blocking
- Allows Python-level processing to overlap with GPU computation
- Significantly reduces per-token latency

**Default State:** Enabled by default in generation loops

---

### Wired Limit Control (Memory Management) ✅

**Implementation:** `wired_limit()` context manager (lines 225-262)

```python
@contextlib.contextmanager
def wired_limit(model: nn.Module, streams: Optional[List[mx.Stream]] = None):
    # Temporarily increase wired working set for Metal GPU
    # On non-Metal (CPU, GPU), this is a no-op
    old_limit = mx.set_wired_limit(max_rec_size)
    try:
        yield
    finally:
        mx.synchronize(streams)  # Wait for pending GPU work
        mx.set_wired_limit(old_limit)  # Restore limit
```

**What it does:**
- Lines 243: Gets device's max recommended working set size
- Line 244-251: Warns if model exceeds 90% of available memory
- Line 253: Temporarily increases wired limit during generation
- Line 258-259: Explicit stream synchronization before restoring limit

**Usage in stream_generate():**
```python
with wired_limit(model, [generation_stream]):
    # All generation happens with increased memory headroom
    for response in stream_generate(...):
        yield response
```

**Default State:**
- Automatically enabled in `stream_generate()` (line 703)
- Automatically managed in `BatchGenerator` (lines 977-988)

---

### Synchronization Points

**Key synchronization operations:**

1. **Line 438:** `mx.eval([c.state for c in prompt_cache])` - Force cache evaluation after prefill chunks
2. **Line 458:** `mx.eval(y)` - Synchronize first generated token
3. **Line 986:** `mx.synchronize(generation_stream)` - Wait for all pending ops in generation stream
4. **Line 1102, 1136, 1165:** Cache state evaluation during batch prefill

**Optimization:** These synchronization points are necessary for correctness but can bottleneck if too frequent.

---

## SUMMARY TABLE: ACTIVATION STATUS

| Feature | Enabled by Default | How to Activate |
|---------|-------------------|-----------------|
| Async evaluation | ✅ Yes | Auto in generate_step |
| Metal streams | ✅ Yes | Auto in stream_generate |
| Wired limit control | ✅ Yes | Auto in stream_generate |
| Compiled sampling | ✅ Yes | Auto via make_sampler |
| Lazy loading | ❌ No | `load(lazy=True)` |
| Prompt caching | ❌ No | `prompt_cache=cache` param |
| KV cache quantization | ❌ No | `kv_bits=4` param |
| Continuous batching | ❌ No | Use `batch_generate()` |
| Batch KV cache | ❌ No | Auto in batch_generate |
| Activation quantization | ❌ No | `model_config={"quantize_activations": True}` |
| Layer fusion | ❌ No | `python -m mlx_lm fuse` |

---

## RECOMMENDED OPTIMIZATIONS FOR YOUR USE CASE

### For Maximum Speed (Latency-Critical):
1. Use `batch_generate()` if you can batch multiple requests
2. Pre-compute prompt caches for system prompts
3. Set `prefill_step_size=2048` (default)
4. Use `completion_batch_size=32` for continuous batching
5. Enable async eval (automatic)

### For Memory Efficiency:
1. Use `kv_bits=4` for KV cache quantization
2. Use `RotatingKVCache` with `max_kv_size=4096`
3. Use `lazy=True` for model loading
4. Use `quantize_activations=True` in model_config

### For Both:
1. Use quantized model weights (4-bit)
2. Implement prompt caching for repeated prefixes
3. Use continuous batching when possible
4. Monitor `peak_memory` from responses

---

## REFERENCES

- Cache Implementation: `/models/cache.py` (1300+ lines)
- Generation Loop: `/generate.py` (1536 lines)  
- Model Loading: `/utils.py` (520+ lines)
- Sampling: `/sample_utils.py` (310 lines)
