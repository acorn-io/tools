package commands

import (
	"context"
	"fmt"

	"github.com/gptscript-ai/go-gptscript"
	"github.com/gptscript-ai/tools/outlook/common/id"
	"github.com/gptscript-ai/tools/outlook/mail/pkg/client"
	"github.com/gptscript-ai/tools/outlook/mail/pkg/global"
	"github.com/gptscript-ai/tools/outlook/mail/pkg/graph"
	"github.com/gptscript-ai/tools/outlook/mail/pkg/printers"
	"github.com/gptscript-ai/tools/outlook/mail/pkg/util"
	"github.com/microsoftgraph/msgraph-sdk-go/models"
)

func ListMessages(ctx context.Context, folderID string) error {
	var (
		trueFolderID string
		err          error
	)

	if folderID != "" {
		trueFolderID, err = id.GetOutlookID(ctx, folderID)
		if err != nil {
			return fmt.Errorf("failed to get folder ID: %w", err)
		}
	}

	c, err := client.NewClient(global.ReadOnlyScopes)
	if err != nil {
		return fmt.Errorf("failed to create client: %w", err)
	}

	messages, err := graph.ListMessages(ctx, c, trueFolderID)
	if err != nil {
		return fmt.Errorf("failed to list mail: %w", err)
	}

	gptscriptClient, err := gptscript.NewGPTScript()
	if err != nil {
		return fmt.Errorf("failed to create GPTScript client: %w", err)
	}

	// Translate Outlook IDs to friendly IDs before we print.
	messageIDs := util.Map(messages, func(message models.Messageable) string {
		return util.Deref(message.GetId())
	})
	translatedMessageIDs, err := id.SetOutlookIDs(ctx, messageIDs)
	if err != nil {
		return fmt.Errorf("failed to translate message IDs: %w", err)
	}

	folderIDs := util.Map(messages, func(message models.Messageable) string {
		return util.Deref(message.GetParentFolderId())
	})
	translatedFolderIDs, err := id.SetOutlookIDs(ctx, folderIDs)
	if err != nil {
		return fmt.Errorf("failed to translate folder IDs: %w", err)
	}

	var elements []gptscript.DatasetElement
	for _, message := range messages {
		message.SetId(util.Ptr(translatedMessageIDs[util.Deref(message.GetId())]))
		message.SetParentFolderId(util.Ptr(translatedFolderIDs[util.Deref(message.GetParentFolderId())]))

		messageStr, err := printers.MessageToString(message, false)
		if err != nil {
			return fmt.Errorf("failed to convert message to string: %w", err)
		}
		elements = append(elements, gptscript.DatasetElement{
			DatasetElementMeta: gptscript.DatasetElementMeta{
				Name:        util.Deref(message.GetId()),
				Description: util.Deref(message.GetSubject()),
			},
			Contents: messageStr,
		})
	}

	datasetID, err := gptscriptClient.CreateDatasetWithElements(ctx, elements, gptscript.DatasetOptions{
		Name:        fmt.Sprintf("%s_outlook_mail", folderID),
		Description: "Outlook mail messages in folder " + folderID,
	})
	if err != nil {
		return fmt.Errorf("failed to create dataset with elements: %w", err)
	}

	fmt.Printf("Created dataset with ID %s with %d messages\n", datasetID, len(messages))
	return nil
}
