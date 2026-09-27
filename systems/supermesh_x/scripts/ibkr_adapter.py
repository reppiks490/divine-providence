#!/usr/bin/env python3
READ_OPS={'portfolio_read','account_read','market_data_read','historical_data_read','orders_read','executions_read','contract_search','scanner_read'}
WRITE_OPS={'place_order','modify_order','cancel_order','transfer_funds','account_change'}


def connection_plan(account_type='retail', preference='web'):
    account_type=(account_type or 'retail').lower(); preference=(preference or 'web').lower()
    if account_type=='retail':
        primary='tws_api' if preference in {'tws','socket'} else 'client_portal_gateway'
    else:
        primary='web_api_oauth2' if preference=='web' else ('tws_api' if preference in {'tws','socket'} else 'fix')
    return {
        'primary_mode':primary,
        'market_data':True,
        'portfolio':True,
        'orders':'gated',
        'requires_user_authentication':True,
        'separate_read_write_authority':True,
        'runtime_checks':['auth','brokerage_session','market_data_entitlements','trading_permissions','pacing_limits','websocket_lifetime']
    }


def authorize_operation(operation, explicit_user_confirmation=False):
    if operation in READ_OPS:
        return {'allowed':True,'permission_class':'read_only'}
    if operation in WRITE_OPS:
        return {'allowed':bool(explicit_user_confirmation),'permission_class':'read_write_gated','requires_explicit_confirmation':True}
    return {'allowed':False,'permission_class':'unknown'}


def authorize_action(action, explicit_confirmation=False):
    mapping={'market.quote':'market_data_read','market.history':'historical_data_read','portfolio.read':'portfolio_read','orders.read':'orders_read','order.place':'place_order','order.modify':'modify_order','order.cancel':'cancel_order'}
    return authorize_operation(mapping.get(action,action), explicit_confirmation)
