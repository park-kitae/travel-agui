"""
tools/flight_tools.py — 항공편 검색 툴
"""
from data.flights import OUTBOUND_DB, INBOUND_DB


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int = 1,
    return_date: str = "",
) -> dict:
    """
    출발지/목적지와 날짜로 항공편을 검색합니다.

    Args:
        origin: 출발 도시 또는 공항 코드 (예: 서울, ICN)
        destination: 도착 도시 또는 공항 코드 (예: 도쿄, NRT)
        departure_date: 출발 날짜 (YYYY-MM-DD)
        passengers: 승객 수
        return_date: 귀국 날짜 (YYYY-MM-DD), 빈 문자열이면 편도

    Returns:
        항공편 검색 결과 (편도 또는 왕복)
    """
    outbound_key = next(
        ((orig, dest) for (orig, dest) in OUTBOUND_DB
         if (orig in origin or origin in orig) and (dest in destination or destination in dest)),
        None,
    )
    if not outbound_key:
        return {"status": "not_found", "message": f"{origin}→{destination} 구간 항공편을 찾을 수 없습니다.", "flights": []}

    outbound_flights = [
        {**f, "departure_date": departure_date, "passengers": passengers,
         "total_price": f["price"] * passengers, "direction": "outbound"}
        for f in OUTBOUND_DB[outbound_key]
    ]

    is_round_trip = bool(return_date)
    inbound_flights = []
    if is_round_trip:
        inbound_key = (outbound_key[1], outbound_key[0])
        if inbound_key in INBOUND_DB:
            inbound_flights = [
                {**f, "departure_date": return_date, "passengers": passengers,
                 "total_price": f["price"] * passengers, "direction": "inbound"}
                for f in INBOUND_DB[inbound_key]
            ]

    result: dict = {
        "status": "success",
        "origin": outbound_key[0],
        "destination": outbound_key[1],
        "departure_date": departure_date,
        "passengers": passengers,
        "trip_type": "round_trip" if is_round_trip else "one_way",
    }
    if is_round_trip:
        result.update({"return_date": return_date, "outbound_flights": outbound_flights,
                        "inbound_flights": inbound_flights, "outbound_count": len(outbound_flights),
                        "inbound_count": len(inbound_flights)})
    else:
        result.update({"flights": outbound_flights, "count": len(outbound_flights)})
    return result
