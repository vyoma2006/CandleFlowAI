export const getPrediction = async (ticker) => {
    // Calling the Python AI Engine directly
    const response = await fetch(`http://localhost:8000/predict/${ticker}`);
    return await response.json(); 
    // Returns: { "ticker": "AAPL", "signal": "BUY", "confidence": 0.87 }
};

export const saveTrade = async (tradeData) => {
    // Calling the Node.js Server to save to MongoDB/Postgres
    const response = await fetch(`http://localhost:5000/api/trades`, {
        method: 'POST',
        body: JSON.stringify(tradeData)
    });
    return await response.json();
};