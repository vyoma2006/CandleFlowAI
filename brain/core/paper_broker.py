import os
import json
from datetime import datetime

STATE_PATH = 'data/paper_wallet_state.json'

class PaperBroker:
    def __init__(self, initial_capital=100000.0):
        self.state_path = STATE_PATH
        self.initial_capital = initial_capital
        self.load_or_initialize_wallet()

    def load_or_initialize_wallet(self):
        """Ingests previous ledger states from disk or boots an empty workspace."""
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r') as f:
                    self.wallet = json.load(f)
                print("💾 Active Paper Broker Ledger loaded cleanly from storage.")
            except:
                self.reset_wallet()
        else:
            self.reset_wallet()

    def reset_wallet(self):
        """Wipes the virtual database back to the initial ₹1 Lakh allocation."""
        self.wallet = {
            "cash": self.initial_capital,
            "equity_curve": [self.initial_capital],
            "active_positions": {}, # Tracks cross-sectional multi-asset targets simultaneously
            "closed_trades_history": []
        }
        self.save_wallet_state()
        print("🧼 Paper Broker Ledger reset to initial ₹1,00,000.00 cash reserve.")

    def save_wallet_state(self):
        """Saves current state metrics to disk safely to survive server reboots."""
        with open(self.state_path, 'w') as f:
            json.dump(self.wallet, f, indent=4)

    def get_portfolio_summary(self, current_prices: dict):
        """
        Calculates live total portfolio valuation, floating PnL, 
        and capital allocations across all assets.
        """
        total_equity = self.wallet["cash"]
        floating_pnl = 0.0
        position_details = []

        for ticker, pos in self.wallet["active_positions"].items():
            if ticker in current_prices:
                live_price = current_prices[ticker]
                entry_price = pos["entry_price"]
                capital = pos["capital"]
                
                # Calculate relative PnL directionally
                pnl_pct = (live_price - entry_price) / entry_price
                if pos["type"] == "SELL":
                    pnl_pct = -pnl_pct
                    
                current_value = capital * (1.0 + pnl_pct)
                current_pnl = capital * pnl_pct
                
                floating_pnl += current_pnl
                total_equity += current_value
                
                position_details.append({
                    "ticker": ticker,
                    "type": pos["type"],
                    "entry_price": entry_price,
                    "live_price": live_price,
                    "allocated_capital": capital,
                    "current_valuation": current_value,
                    "pnl": current_pnl,
                    "pnl_pct": pnl_pct * 100,
                    "stop_loss": pos["stop_loss"],
                    "take_profit": pos["take_profit"]
                })

        return {
            "cash": round(self.wallet["cash"], 2),
            "total_equity": round(total_equity, 2),
            "floating_pnl": round(floating_pnl, 2),
            "active_positions": position_details,
            "trade_counts": len(self.wallet["closed_trades_history"])
        }

    def open_position_live(self, ticker: str, direction: str, close_price: str, net_spread: float, atr_buffer: float):
        """Validates entry margins and mounts an active position envelope inside memory state."""
        if ticker in self.wallet["active_positions"]:
            return False  # Position already open for this specific asset vector
            
        # Sizing calculations mirror backtester structures
        allocated_capital = self.wallet["cash"] * 0.50 if net_spread < 0.12 else self.wallet["cash"] * 1.0
        
        if self.wallet["cash"] < allocated_capital or allocated_capital < 1000:
            return False # Insufficient liquid reserves available

        # Subtract capital out of liquid cash pool balance
        self.wallet["cash"] -= allocated_capital

        # Risk boundary setup matching the backtest configuration
        if direction == "BUY":
            stop_loss = close_price - (1.5 * atr_buffer)
            take_profit = close_price + (3.0 * atr_buffer)
        else:
            stop_loss = close_price + (1.5 * atr_buffer)
            take_profit = close_price - (3.0 * atr_buffer)

        self.wallet["active_positions"][ticker] = {
            "type": direction,
            "entry_price": close_price,
            "capital": allocated_capital,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.save_wallet_state()
        print(f"🟢 virtual Order Executed: {direction} {ticker} at ₹{close_price:.2f} | Risk Brackets Set.")
        return True

    def scan_active_positions_for_exits(self, current_prices: dict):
        """Scans floating positions to check if trailing risk brackets have been tripped."""
        exits_triggered = False
        active_tickers = list(self.wallet["active_positions"].keys())

        for ticker in active_tickers:
            if ticker not in current_prices: continue
            
            pos = self.wallet["active_positions"][ticker]
            live_price = current_prices[ticker]
            
            is_tp = False
            is_sl = False

            if pos["type"] == "BUY":
                if live_price >= pos["take_profit"]: is_tp = True
                elif live_price <= pos["stop_loss"]: is_sl = True
            else: # SELL
                if live_price <= pos["take_profit"]: is_tp = True
                elif live_price >= pos["stop_loss"]: is_sl = True

            if is_tp or is_sl:
                # Realize and close out trade allocation
                pnl_pct = (live_price - pos["entry_price"]) / pos["entry_price"]
                if pos["type"] == "SELL": pnl_pct = -pnl_pct
                
                realized_pnl = pos["capital"] * pnl_pct
                returned_capital = pos["capital"] + realized_pnl
                
                # Re-inject capital back into the liquid cash reserves balance
                self.wallet["cash"] += returned_capital
                
                closed_record = {
                    "ticker": ticker,
                    "type": pos["type"],
                    "entry_price": pos["entry_price"],
                    "exit_price": live_price,
                    "pnl": realized_pnl,
                    "result": "TP" if is_tp else "SL",
                    "closed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                self.wallet["closed_trades_history"].append(closed_record)
                del self.wallet["active_positions"][ticker]
                exits_triggered = True
                print(f"🔴 Virtual Exit Triggered: {ticker} closed via {closed_record['result']} | Net PnL: ₹{realized_pnl:.2f}")

        if exits_triggered:
            self.save_wallet_state()