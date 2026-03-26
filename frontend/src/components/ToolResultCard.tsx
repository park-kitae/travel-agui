import { Hotel, Flight, ToolSnapshot, HotelSearchResult, FlightSearchResult, TravelTipsResult } from '../types'

interface Props {
  snapshot: ToolSnapshot
}

export function ToolResultCard({ snapshot }: Props) {
  const { tool, result } = snapshot

  if (tool === 'search_hotels') {
    return <HotelCard data={result as HotelSearchResult} />
  }
  if (tool === 'search_flights') {
    return <FlightCard data={result as FlightSearchResult} />
  }
  if (tool === 'get_travel_tips') {
    return <TipsCard data={result as TravelTipsResult} />
  }
  return null
}

// ── 호텔 카드 ──────────────────────────────────
function HotelCard({ data }: { data: HotelSearchResult }) {
  if (data.status !== 'success' || !data.hotels?.length) return null
  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">🏨</span>
        <span className="tool-title">
          {data.city} 호텔 검색결과
        </span>
        <span className="tool-meta">
          {data.check_in} ~ {data.check_out} · {data.guests}명
        </span>
      </div>
      <div className="hotel-grid">
        {data.hotels!.map((h, i) => (
          <HotelItem key={i} hotel={h} />
        ))}
      </div>
    </div>
  )
}

function HotelItem({ hotel }: { hotel: Hotel }) {
  return (
    <div className="hotel-item">
      <div className="hotel-stars">{'★'.repeat(hotel.stars)}{'☆'.repeat(5 - hotel.stars)}</div>
      <div className="hotel-name">{hotel.name}</div>
      <div className="hotel-area">{hotel.area}</div>
      <div className="hotel-footer">
        <span className="hotel-rating">⭐ {hotel.rating}</span>
        <span className="hotel-price">{hotel.price.toLocaleString()}원<small>/박</small></span>
      </div>
    </div>
  )
}

// ── 항공 카드 ──────────────────────────────────
function FlightCard({ data }: { data: FlightSearchResult }) {
  if (data.status !== 'success') return null

  const isRoundTrip = data.trip_type === 'round_trip'
  const hasFlights = isRoundTrip
    ? (data.outbound_flights?.length || data.inbound_flights?.length)
    : data.flights?.length

  if (!hasFlights) return null

  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">✈️</span>
        <span className="tool-title">
          {data.origin} ↔ {data.destination} {isRoundTrip ? '왕복' : '편도'}
        </span>
        <span className="tool-meta">
          {data.departure_date} {isRoundTrip && data.return_date && `~ ${data.return_date}`} · {data.passengers}명
        </span>
      </div>

      {/* 왕복 항공편 */}
      {isRoundTrip ? (
        <>
          {data.outbound_flights && data.outbound_flights.length > 0 && (
            <div className="flight-section">
              <div className="flight-section-title">출발편 ({data.origin} → {data.destination})</div>
              <div className="flight-list">
                {data.outbound_flights.map((f, i) => (
                  <FlightItem key={`out-${i}`} flight={f} />
                ))}
              </div>
            </div>
          )}

          {data.inbound_flights && data.inbound_flights.length > 0 && (
            <div className="flight-section">
              <div className="flight-section-title">귀국편 ({data.destination} → {data.origin})</div>
              <div className="flight-list">
                {data.inbound_flights.map((f, i) => (
                  <FlightItem key={`in-${i}`} flight={f} />
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        /* 편도 항공편 */
        <div className="flight-list">
          {data.flights!.map((f, i) => (
            <FlightItem key={i} flight={f} />
          ))}
        </div>
      )}
    </div>
  )
}

function FlightItem({ flight }: { flight: Flight }) {
  return (
    <div className="flight-item">
      <div className="flight-airline">
        <span className="airline-name">{flight.airline}</span>
        <span className="flight-code">{flight.flight}</span>
        <span className="flight-class-badge">{flight.class}</span>
      </div>
      <div className="flight-route">
        <span className="flight-time">{flight.depart}</span>
        <span className="flight-arrow">
          <span className="flight-duration">{flight.duration}</span>
          <span className="flight-line">──────✈</span>
        </span>
        <span className="flight-time">{flight.arrive}</span>
      </div>
      <div className="flight-price">{flight.total_price.toLocaleString()}원</div>
    </div>
  )
}

// ── 여행 팁 카드 ──────────────────────────────
function TipsCard({ data }: { data: TravelTipsResult }) {
  if (data.status !== 'success') return null
  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">🗺️</span>
        <span className="tool-title">{data.destination} 여행 정보</span>
        <span className="tool-meta">{data.best_season}</span>
      </div>
      <p className="tips-overview">{data.overview}</p>
      <div className="tips-grid">
        {data.spots?.length && (
          <div className="tips-section">
            <div className="tips-section-title">📍 주요 관광지</div>
            <ul>{data.spots.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        )}
        {data.food?.length && (
          <div className="tips-section">
            <div className="tips-section-title">🍜 추천 음식</div>
            <ul>{data.food.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
        {data.tips?.length && (
          <div className="tips-section">
            <div className="tips-section-title">💡 여행 팁</div>
            <ul>{data.tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
          </div>
        )}
      </div>
      <div className="tips-meta-row">
        <span>💱 {data.currency}</span>
        <span>🗣️ {data.language}</span>
      </div>
    </div>
  )
}
