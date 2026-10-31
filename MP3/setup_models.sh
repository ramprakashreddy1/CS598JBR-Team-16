# Current Colab PyTorch uses CUDA 13; 0.47.0 only ships binaries through 12.9.
pip3 install bitsandbytes==0.50.2
pip3 install transformers==4.55.4
pip3 install peft==0.4.0
pip3 install accelerate==1.10.1
pip3 install einops==0.6.1
pip3 install evaluate==0.4.0
# 0.1.99 has no CPython 3.13 wheel and fails to build on current Colab.
pip3 install sentencepiece==0.2.2
