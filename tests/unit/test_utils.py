import unittest
import json
from parameterized import parameterized
from xian.utils.encoding import extract_payload_string, decode_transaction_bytes, encode_transaction_bytes
from xian.utils.tx import unpack_transaction, verify

class TestPayloadStrExtraction(unittest.TestCase):

    @parameterized.expand([
        (
            "preserve_payload_as_string",
            '{"metadata":{"signature":"f47871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f05"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST"},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            True
        ),
        (
            "preserve_payload_with_nested_json_as_string",
            '{"metadata":{"signature":"f47871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f05"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST","nested_data":{"key1":"value1","key2":{"subkey":"subvalue"}}},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            True
        ),
        (
            "preserve_payload_with_deeply_nested_json_as_string",
            '{"metadata":{"signature":"f47871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f05"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST","nested_data":{"key1":"value1","key2":{"subkey":"subvalue","deeper":{"deep_key":"deep_value","deep_array":[{"array_key1":"array_value1"},{"array_key2":"array_value2"}]}}}},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            True
        ),
        (
            "bracket_in_payload_string",
            '{"metadata":{"signature":"f47871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f05"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST}"},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            True
        ),
        (
            "no_payload_field",
            '{"id": 2, "other_field": "data"}',
            False
        ),
        (
            "empty_payload",
            '{"id": 3, "payload": "", "other_field": "data"}',
            False
        ),
        (
            "escaped_quotes_in_payload",
            '{"metadata":{"signature":"abc"},"payload":{"text":"This is a \\"quoted\\" string","number":123}}',
            True
        ),
        (
            "special_characters_in_payload",
            '{"metadata":{"signature":"abc"},"payload":{"text":"Special characters !@#$%^&*()_+-=~`"}}',
            True
        ),
        (
            "payload_with_empty_object",
            '{"metadata":{"signature":"abc"},"payload":{}}',
            True
        ),
        (
            "payload_with_empty_array",
            '{"metadata":{"signature":"abc"},"payload":{"array":[]}}',
            True
        ),
        (
            "payload_with_large_numbers",
            '{"metadata":{"signature":"abc"},"payload":{"large_number":12345678901234567890}}',
            True
        ),
        (
            "payload_with_unicode_characters",
            '{"metadata":{"signature":"abc"},"payload":{"text":"Unicode test: \u2603 \u2764"}}',
            True
        ),
        (
            "payload_with_boolean_values",
            '{"metadata":{"signature":"abc"},"payload":{"flag":true,"status":false}}',
            True
        ),
        (
            "payload_with_null_value",
            '{"metadata":{"signature":"abc"},"payload":{"nullable":null}}',
            True
        )
    ])
    def test_extract_payload(self, name, tx_str, has_payload, should_match=True):
        complete_json = json.loads(tx_str)
        if has_payload:
            result = json.loads(extract_payload_string(tx_str))
            if should_match:
                self.assertEqual(result, complete_json['payload'])
            else:
                self.assertNotEqual(result, complete_json['payload'])
        else:
            with self.assertRaises(ValueError):
                res = extract_payload_string(tx_str)
                breakpoint()
                

class TestVerification(unittest.TestCase):
    @parameterized.expand([
        (
            "valid_transaction",
            '{"metadata":{"signature":"f47871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f05"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST"},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            True
        ),
        (
            "invalid_signature",
            '{"metadata":{"signature":"f47871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f04"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST"},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            False
        )
    ])
    def test_verify(self, name, tx_str, expected_result):
        tx_json = json.loads(tx_str)
        payload_str = extract_payload_string(tx_str)
        sender, signature, payload = unpack_transaction(tx_json)
        self.assertEqual(verify(sender, payload_str, signature), expected_result)
        
class TestEncoding(unittest.TestCase):
    @parameterized.expand([
        (
            "valid_transaction",
            '{"metadata":{"signature":"f47871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f05"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST"},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            False
        ),
        (
            "multiple_payload_fields",
            '{"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":10000000000,"to":"JAVASCRIPT_TRANSACTION_TEST"},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}, "metadata":{"signature":"847871676c33d17d5a86bd8b2f12832e35e2b73692b0f28321be2f9acd3379c755440333ddc5e5bf40255256adb946aecae6729e8cb3a9028b08cdd995609f05"},"payload":{"chain_id":"xian-local","contract":"currency","function":"transfer","kwargs":{"amount":0.00000252,"to":"JAVASCRIPT_TRANSACTION_TEST"},"nonce":40,"sender":"e9e8aad29ce8e94fd77d9c55582e5e0c57cf81c552ba61c0d4e34b0dc11fd931","stamps_supplied":10}}',
            True
        )
    ])
    def test_decode_transaction_bytes(self, name, tx_str, should_raise):
        tx_bytes = encode_transaction_bytes(tx_str)
        if should_raise:
            with self.assertRaises(AssertionError) as context:
                tx_json_decoded, payload_str = decode_transaction_bytes(tx_bytes)
            self.assertTrue('Invalid payload' in str(context.exception))
        else:
            tx_json_decoded, payload_str = decode_transaction_bytes(tx_bytes)
        # self.assertEqual(tx_json_decoded, tx_json)
                
if __name__ == '__main__':
    unittest.main()
