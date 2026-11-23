# CryptoTrace Web

CryptoTrace is a Streamlit dashboard for exploring Ethereum transaction flows, known wallet labels, and estimated fund reconciliation.

## Start from a fresh checkout

You need Python 3.10 or newer. Open a terminal in the project folder (the folder containing `app.py`), then create and activate a virtual environment.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed in the terminal, usually <http://localhost:8501>. Stop the server with `Ctrl+C`.

## Try the demo

Demo mode is on by default and works offline; no `.env` file or API key is required. Select **Wallet example** under Quick demo, then click **Run investigation**. The sample trace ends at labeled Binance and Kraken exchange endpoints. These are synthetic demo results, not live blockchain activity.

## Configure live Etherscan access (optional)

Create a `.env` file in the project folder if you do not already have one, and add your Etherscan API key:

```dotenv
ETHERSCAN_API_KEY=replace_with_your_etherscan_key
```

The default Etherscan API URL is already configured. Keep `.env` private and never commit or share API keys. Restart the app after changing `.env`. In the dashboard, turn off **Demo mode** to run a live investigation; the API key can also be entered in the sidebar.

## Scope and limitations

- Ethereum Mainnet, native ETH transfers only; ERC-20 tracing is not implemented.
- Wallet input begins from the wallet's current ETH balance, not a known stolen amount.
- Endpoint labels come from the local `data/exchanges.json` lookup and are not proof of misconduct.
- Proportional fund-flow allocation is an analytical estimate, not forensic proof that identifiable units of ETH moved between addresses.
- This is a local prototype. Before public deployment, add authentication, rate limiting, secret management, and appropriate operational controls.
0x0a784e0C41Dee3055ED881E19430CE09CC04a2B4