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

from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import get_suite

def test_ragas_sample_markdown_registered():
    suite = get_suite("ragas_sample_markdown")
    assert isinstance(suite, BaseSuite)
    assert suite.name == "ragas_sample_markdown"
