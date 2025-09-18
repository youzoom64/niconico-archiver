class ConfigUtils:
    @staticmethod
    def merge_config_deep(default, loaded):
        """設定を深くマージして不足項目を補完"""
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = ConfigUtils.merge_config_deep(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def validate_argument_config(arg_config):
        """引数設定の妥当性チェック"""
        required_fields = []  # 必須フィールドなし（柔軟性重視）
        allowed_fields = ["required", "type", "choices", "default", "help"]
        
        for field in arg_config:
            if field not in allowed_fields:
                return False, f"無効なフィールド: {field}"
        
        # typeの値チェック
        if "type" in arg_config:
            if arg_config["type"] not in ["str", "int", "float", "bool"]:
                return False, f"無効なtype: {arg_config['type']}"
        
        return True, "OK"