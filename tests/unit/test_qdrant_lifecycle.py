# Copyright (C) 2026 Andrea Marson (am.dev.75@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from retriva_eval.adapters.qdrant_store import QdrantAdapter
from retriva_eval.core.config import Settings

def test_safe_delete_collection(caplog):
    settings = Settings()
    adapter = QdrantAdapter(settings)
    adapter.safe_delete_collection()
    
    assert "Deletion of collection" in caplog.text
    assert "disabled in MVP" in caplog.text
    # Ensure client.delete_collection is not called (implicitly because we don't mock it and it didn't throw connection error)
