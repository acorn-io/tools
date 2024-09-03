package commands

import (
	"context"
	"fmt"

	"github.com/gptscript-ai/tools/apis/outlook/common/id"
	"github.com/gptscript-ai/tools/apis/outlook/mail/code/pkg/client"
	"github.com/gptscript-ai/tools/apis/outlook/mail/code/pkg/global"
	"github.com/gptscript-ai/tools/apis/outlook/mail/code/pkg/graph"
)

func DeleteMessage(ctx context.Context, messageID string) error {
	trueMessageID, err := id.GetOutlookID(messageID)
	if err != nil {
		return fmt.Errorf("failed to get message ID: %w", err)
	}

	c, err := client.NewClient(global.AllScopes)
	if err != nil {
		return fmt.Errorf("failed to create client: %w", err)
	}

	if err := graph.DeleteMessage(ctx, c, trueMessageID); err != nil {
		return fmt.Errorf("failed to delete message: %w", err)
	}

	fmt.Println("Message deleted successfully")
	return nil
}
