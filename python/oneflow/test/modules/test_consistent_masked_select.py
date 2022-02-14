"""
Copyright 2020 The OneFlow Authors. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import unittest

import oneflow as flow
import oneflow.unittest

from oneflow.test_utils.automated_test_util import *


@autotest(check_graph=False)
def _test_masked_select(test_case, placement, sbp):
    k1 = random().to(int).value() * 8
    k2 = random().to(int).value() * 8
    input = random_tensor(ndim=2, dim0=k1, dim1=k2).to_global(placement, sbp)
    mask = input.ge(0.5)
    return torch.masked_select(input, mask)


@autotest(check_graph=False)
def _test_masked_select_broadcast(test_case, placement, sbp):
    k1 = random().to(int).value() * 8
    k2 = random().to(int).value() * 8
    input = random_tensor(ndim=4, dim0=k1, dim1=k2, dim2=1, dim3=k2).to_global(
        placement, sbp
    )
    mask = random_tensor(ndim=4, dim0=k1, dim1=k2, dim2=k1, dim3=1).to_global(
        placement, sbp
    )
    return torch.masked_select(input, mask > 0.5)


class TestMaskedSelect(flow.unittest.TestCase):
    @global_view
    def test_masked_select(test_case):
        for placement in all_placement():
            for sbp in all_sbp(placement, max_dim=2):
                _test_masked_select(test_case, placement, sbp)
                _test_masked_select_broadcast(test_case, placement, sbp)


if __name__ == "__main__":
    unittest.main()
