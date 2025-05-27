import asyncio
import argparse
import json
import logging
import sys

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, ConsumerStoppedError

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def consume_messages(topic: str, bootstrap_servers: str, group_id: str):
    consumer = None
    while True:  # Outer loop for retrying connection
        try:
            logger.info(f"Attempting to connect to Kafka: {bootstrap_servers}")
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                # auto_offset_reset="earliest",  # Start from the beginning of the topic if group is new
                # enable_auto_commit=True, # Default is True
                # auto_commit_interval_ms=5000 # Default is 5000
            )
            await consumer.start()
            logger.info(
                f"Successfully started Kafka consumer for topic '{topic}' with group '{group_id}'. Waiting for messages..."
            )

            async for msg in consumer:
                try:
                    logger.info(
                        f"Consumed message: topic={msg.topic}, partition={msg.partition}, offset={msg.offset}, "
                        f"key={msg.key.decode('utf-8') if msg.key else None}"
                    )

                    message_value_str = msg.value.decode("utf-8")
                    try:
                        # Attempt to parse as JSON for pretty printing
                        message_value_json = json.loads(message_value_str)
                        pretty_value = json.dumps(
                            message_value_json, indent=2, sort_keys=True
                        )
                        print("--- Message Value (JSON) ---")
                        print(pretty_value)
                    except json.JSONDecodeError:
                        # If not JSON, print as plain text
                        print("--- Message Value (Text) ---")
                        print(message_value_str)
                    print("-----------------------------")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except KafkaConnectionError as kce:
            logger.error(f"Kafka connection error: {kce}. Retrying in 10 seconds...")
            if consumer:
                try:
                    await consumer.stop()
                except Exception as stop_e:
                    logger.error(f"Error stopping consumer during retry: {stop_e}")
            consumer = None  # Ensure re-initialization
            await asyncio.sleep(10)
        except ConsumerStoppedError:
            logger.info("Consumer stopped as expected.")
            break  # Exit retry loop if consumer was intentionally stopped
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Shutting down consumer...")
            break
        except Exception as e:
            logger.error(
                f"An unexpected error occurred: {e}. Retrying in 10 seconds...",
                exc_info=True,
            )
            if consumer:
                try:
                    await consumer.stop()
                except Exception as stop_e:
                    logger.error(
                        f"Error stopping consumer during unexpected error: {stop_e}"
                    )
            consumer = None
            await asyncio.sleep(10)
        finally:
            if consumer:
                logger.info("Stopping consumer...")
                try:
                    await consumer.stop()
                    logger.info("Consumer stopped successfully.")
                except Exception as e:
                    logger.error(f"Error stopping Kafka consumer: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Kafka Inspector: Consumes and prints messages from a Kafka topic."
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="claim-facts",
        help="Kafka topic to consume from (default: claim-facts)",
    )
    parser.add_argument(
        "--servers",
        type=str,
        default="localhost:9092",
        help="Kafka bootstrap servers (comma-separated, default: localhost:9092)",
    )
    parser.add_argument(
        "--group-id",
        type=str,
        default="kafka-inspector-group",
        help="Kafka consumer group ID (default: kafka-inspector-group)",
    )

    args = parser.parse_args()

    logger.info(
        f"Starting Kafka Inspector for topic: {args.topic}, servers: {args.servers}, group: {args.group_id}"
    )

    try:
        asyncio.run(consume_messages(args.topic, args.servers, args.group_id))
    except KeyboardInterrupt:
        logger.info("Kafka Inspector shut down by user.")
    except Exception as e:
        logger.error(f"Kafka Inspector exited with an error: {e}", exc_info=True)
    finally:
        logger.info("Kafka Inspector finished.")
